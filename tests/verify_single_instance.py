#!/usr/bin/env python3
"""Exercise the actual cross-assembly instance lease and inactive-abort guard.

On Windows the helper uses the named semaphore used by GTA V. On Linux its
exclusive-file fallback is exercised. These tests do not run GTA V or SHVDN.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'Mod/scripts/CinnamonCoffee.3.cs').read_text(encoding='utf-8-sig')
lease = source.split('// PROCESS-WIDE CINNAMONCOFFEE INSTANCE LEASE', 1)[1].split(
    '// END PROCESS-WIDE CINNAMONCOFFEE INSTANCE LEASE', 1)[0]


def method(signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


constructor = method('public CinnamonCoffee()')
abort = method('private void OnAborted(object sender, EventArgs e)')
assert constructor.index('TryAcquire(out _instanceLease)') < constructor.index('Tick    += OnTick;')
assert constructor.index('TryAcquire(out _instanceLease)') < constructor.index('_telemetry = new TelemetrySender();')
assert 'private readonly TelemetrySender _telemetry = new' not in source
assert 'if (ownedLease == null) return;' in abort and 'ownedLease.Dispose();' in abort
assert 'CinnamonCoffeeStartup.log' in source and 'file=" + Filename' in source
assert 'semaphore.WaitOne(0)' in lease and 'Semaphore(1, 1,' in lease
assert 'catch (Exception exception)' in constructor and '_instanceLease.Dispose();' in constructor
assert 'Tick -= OnTick;' in constructor and 'Aborted -= OnAborted;' in constructor

dotnet = Path(sys.argv[1] if len(sys.argv) > 1 else
              shutil.which('dotnet') or '/workspace/tools/csharp/dotnet/dotnet').resolve()
csc = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name
prefix = 'using System; using System.IO; using System.Reflection; using System.Threading;\n'
library = prefix + 'namespace CinnamonCoffee {\n' + lease + '\n}\n'

driver = prefix + r'''
class Ped { public TaskInvoker Task = new TaskInvoker(); public bool IsPositionFrozen; public bool Exists() { return true; } }
class TaskInvoker { public int Cleared; public void ClearAll() { Cleared++; } }
class Player { public Ped Character = new Ped(); }
static class Game { public static Player Player = new Player(); }
enum Hash { SET_ENTITY_COLLISION }
static class Function { public static int Calls; public static void Call(Hash hash, params object[] args) { Calls++; } }
class Resource : IDisposable { public int Disposed; public void Dispose() { Disposed++; } }
namespace CinnamonCoffee {
''' + lease + r'''
class Harness {
    private CinnamonCoffeeInstanceLease _instanceLease;
    private Resource _waveMixer = new Resource();
    private Resource _telemetry = new Resource();
    private int resets;
    private void FullReset() { resets++; }
''' + abort + r'''
    private static int checks;
    private static void Check(bool value, string message) {
        checks++; if (!value) throw new Exception("FAIL: " + message);
    }
    private static bool Acquire(Type type, out IDisposable lease) {
        object[] args = new object[] { null };
        bool acquired = (bool)type.GetMethod("TryAcquire", BindingFlags.Static | BindingFlags.Public).Invoke(null, args);
        lease = (IDisposable)args[0];
        return acquired;
    }
    public static void Main(string[] args) {
        Type a = Assembly.LoadFile(args[0]).GetType("CinnamonCoffee.CinnamonCoffeeInstanceLease", true);
        Type b = Assembly.LoadFile(args[1]).GetType("CinnamonCoffee.CinnamonCoffeeInstanceLease", true);
        Check(a.Assembly != b.Assembly, "independently compiled assemblies exercise distinct static storage");
        IDisposable primary, duplicate;
        Check(Acquire(a, out primary), "first compiled script becomes owner");
        Check(!Acquire(b, out duplicate) && duplicate == null, "copy in another assembly cannot become owner");
        Check(!Acquire(a, out duplicate), "same assembly cannot acquire twice on the same thread");
        var inactive = new Harness();
        inactive.OnAborted(null, EventArgs.Empty);
        Check(inactive.resets == 0 && inactive._waveMixer.Disposed == 0 && inactive._telemetry.Disposed == 0,
            "inactive duplicate abort does not reset tasks or dispose active audio resources");
        Check(Game.Player.Character.Task.Cleared == 0 && Function.Calls == 0,
            "inactive abort never calls game task/collision cleanup");
        Check(!Acquire(b, out duplicate), "inactive abort cannot release primary instance ownership");
        Exception backgroundFailure = null;
        var disposal = new Thread(() => { try { primary.Dispose(); } catch (Exception e) { backgroundFailure = e; } });
        disposal.Start(); disposal.Join();
        Check(backgroundFailure == null, "owner can release on a different thread");
        primary.Dispose();
        Check(Acquire(b, out duplicate), "reload can acquire after former owner releases");
        duplicate.Dispose();

        var start = new ManualResetEvent(false);
        Thread[] contenders = new Thread[16];
        IDisposable[] winners = new IDisposable[16];
        Exception[] errors = new Exception[16];
        for (int i = 0; i < contenders.Length; i++) {
            int slot = i;
            contenders[i] = new Thread(() => {
                try { start.WaitOne(); IDisposable acquired; if (Acquire(slot % 2 == 0 ? a : b, out acquired)) winners[slot] = acquired; }
                catch (Exception e) { errors[slot] = e; }
            });
            contenders[i].Start();
        }
        start.Set();
        foreach (Thread thread in contenders) thread.Join();
        int count = 0;
        foreach (IDisposable winner in winners) if (winner != null) count++;
        Check(count == 1, "16 racing copies across two assemblies produce exactly one owner");
        foreach (Exception error in errors) Check(error == null, "racing loser returns inactive without exception");
        foreach (IDisposable winner in winners) if (winner != null) winner.Dispose();
        var active = new Harness();
        Check(CinnamonCoffeeInstanceLease.TryAcquire(out active._instanceLease), "runtime harness can become owner after race");
        active.OnAborted(null, EventArgs.Empty);
        Check(active.resets == 1 && active._waveMixer.Disposed == 1 && active._telemetry.Disposed == 1,
            "active owner cleanup executes exactly once");
        Check(Game.Player.Character.Task.Cleared == 1 && Function.Calls == 1, "active owner releases gameplay state");
        active.OnAborted(null, EventArgs.Empty);
        Check(active.resets == 1 && Game.Player.Character.Task.Cleared == 1, "repeated abort cannot clean up another owner");
        Check(Acquire(a, out primary), "owner abort releases process lease for script reload");
        primary.Dispose();
        Console.WriteLine("PASS: " + checks + " cross-assembly single-instance/abort assertions; no GTA V runtime.");
    }
}
}
'''

with tempfile.TemporaryDirectory(prefix='cinnamon-instance-tests-') as directory:
    temp = Path(directory)
    rsp = temp / 'refs.rsp'
    rsp.write_text('\n'.join('/r:' + str(p) for p in refs.glob('*.dll')))

    def compile_(name, contents, target):
        cs = temp / (name + '.cs')
        dll = temp / (name + '.dll')
        cs.write_text(contents)
        subprocess.run([str(dotnet), str(csc), '/nologo', '/target:' + target, '/langversion:5',
                        '/nostdlib+', '@' + str(rsp), '/out:' + str(dll), str(cs)], check=True)
        return dll

    a = compile_('CopyA', library, 'library')
    b = compile_('CopyB', library, 'library')
    exe = compile_('InstanceTests', driver, 'exe')
    (temp / 'InstanceTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net8.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': runtime}}}))
    subprocess.run([str(dotnet), str(exe), str(a), str(b)], check=True)
print('PASS: constructor ownership precedes events/resources; startup log records version and source path.')
