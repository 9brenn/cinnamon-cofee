#!/usr/bin/env python3
"""Exercise actual J/Finish input and transition slices without a GTA V process.

Usage: python3 tests/verify_finish_flow.py [source.cs] [dotnet]
Requires the .NET 8 SDK. Native calls are mocked, so this verifies input/state
ownership and transition timing, not in-game animation rendering.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'Mod/scripts/CinnamonCoffee.3.cs'
source = source_path.read_text(encoding='utf-8-sig')


def method(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == '{':
            depth += 1
        elif source[position] == '}':
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError('Unclosed method: ' + signature)


simple = method('private bool HasSimpleFinishMenu()')
street_protection = source.split('// STREET FINISH PROTECTION', 1)[1].split('// END STREET FINISH PROTECTION', 1)[0]
master_input = source.split('// KEYBOARD MASTER INPUT', 1)[1].split('// END KEYBOARD MASTER INPUT', 1)[0]
version_declaration = re.search(r'private const string SCRIPT_VERSION = [^;]+;', source).group(0)
master = method('private void HandleAnimationMasterMenu()')
close_live = method('private void CloseLiveVoiceMenu()')
keyboard = method('private void OnKeyDown(object sender, KeyEventArgs e)')
keyboard = keyboard.split('            int itemCount', 1)[0] + ' GeneralHandlerReached = true; }'
controller = method('private void HandleControllerMenuInput()')
controller = controller.split('            int itemCount', 1)[0] + ' GeneralHandlerReached = true; }'
poll_release = method('private void PollLiveVoiceMenuToggle()')
poll_release = poll_release.split('            bool keyDown', 1)[0] + ' }'
poll_release = poll_release.replace('PollLiveVoiceMenuToggle()', 'PollMasterRelease()')

animating = method('private void HandleAnimatingState(Ped player)')
tick = animating.split('// The live voice overlay consumes its close button without finishing the animation.', 1)[1]
tick = tick.split('// Execute the actual finish once the Finish menu choice is resolved', 1)[0]
assert 'HandleAnimationMasterMenu();' in tick, 'Animation tick must delegate master input to task-free menu handler'
assert all(name not in tick for name in ('EndAnimation(', 'STOP_ANIM_TASK', 'TASK_PLAY_ANIM', 'ClearAll(', 'animPhase ='))
tick = 'private void TickMasterInput() {' + tick + '}'

select = method('private void HandleMenuSelect()')
select = select.split('else if (menuLevel == MenuLevel.Finish)', 1)[1]
select = select.split('// ── A-Life: full Ask', 1)[0].strip()
assert select.startswith('{')
select = 'private void SelectFinishChoice() ' + select + ' }'
options = method('private int GetCurrentMenuItemCount()')
options = options.split('else if (menuLevel == MenuLevel.Finish)', 1)[1].split('else if (menuLevel == MenuLevel.Approach)', 1)[0].strip()
options = 'private int FinishOptionCount() ' + options
draw = method('private void DrawFinishMenu(float x, ref float y, float lh)')

pending = animating.split('// Execute the actual finish once the Finish menu choice is resolved', 1)[1]
special = '// Kissing: start outro' + pending.split('// Kissing: start outro', 1)[1].split('if (mode == Mode.Car && animPhase == 2)', 1)[0]
pending_guard = pending.split('{', 1)[0]
pending_guard = 'private void ExecuteSimplePending(Ped player) {' + pending_guard + '{ _finishExecutePending = false;'
pending_guard += special + '} }'

back = keyboard  # Test only the actual Finish-specific back branch below.
full_keyboard = method('private void OnKeyDown(object sender, KeyEventArgs e)')
back = full_keyboard.split('else if (menuLevel == MenuLevel.Finish)', 1)[1]
back = back[:back.index('                else')].strip()
back = 'private void BackFromFinish() ' + back

dotnet = Path(sys.argv[2] if len(sys.argv) > 2 else
              shutil.which('dotnet') or '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name

mocks = r'''
using System;
using System.Collections.Generic;
using System.IO;
enum Keys { J, Back, NumPad5 }
class KeyEventArgs { public Keys KeyCode; }
enum ScriptState { Idle, Animating }
enum MenuLevel { None, Finish, PartnerVoices, Main, Club }
enum ClubDancePhase { Off }
enum Mode { Car, Street }
struct Vector3 {
    public float X,Y,Z;
    public Vector3(float x,float y,float z) { X=x;Y=y;Z=z; }
    public float DistanceTo(Vector3 other) {
        return (float)Math.Sqrt((X-other.X)*(X-other.X)+(Y-other.Y)*(Y-other.Y)+(Z-other.Z)*(Z-other.Z));
    }
}
class Ped {
    public float Heading, Playhead; public bool Outro;
    public int Handle; public bool IsAlive=true;
    public Vector3 Position,Rotation;
    public bool Exists() { return true; }
    public bool IsInVehicle() { return false; }
    public Vector3 GetOffsetPosition(Vector3 offset) { return offset; }
}
enum Hash : ulong {
    IS_DISABLED_CONTROL_PRESSED, IS_DISABLED_CONTROL_JUST_PRESSED,
    SET_ENTITY_ANIM_CURRENT_TIME, SET_ENTITY_ANIM_SPEED,
    SET_ENTITY_COORDS_NO_OFFSET, TASK_PLAY_ANIM, GET_ANIM_DURATION,
    DISABLE_ALL_CONTROL_ACTIONS,ENABLE_CONTROL_ACTION,GET_ENTITY_ANIM_CURRENT_TIME,
    IS_ENTITY_PLAYING_ANIM,HAS_ANIM_DICT_LOADED,TASK_PLAY_ANIM_ADVANCED
}
class Player { public Ped Character; }
static class Game {
    public static bool Held; public static int GameTime = 1000;
    public static Player Player=new Player();
    public static bool IsKeyPressed(Keys key) { return key==Keys.J && Held; }
}
static class Function {
    public static bool MasterHeld, MasterPressed, BackPressed;
    public static int Mutations;
    public static T Call<T>(Hash hash, params object[] args) {
        object value;
        if (hash == Hash.IS_DISABLED_CONTROL_PRESSED) value = MasterHeld;
        else if (hash == Hash.IS_DISABLED_CONTROL_JUST_PRESSED)
            value = (int)args[1] == 1 ? MasterPressed : BackPressed;
        else if (hash == Hash.GET_ANIM_DURATION) value = 1.0f;
        else if (hash == Hash.GET_ENTITY_ANIM_CURRENT_TIME) value=((Ped)args[0]).Playhead;
        else if (hash == Hash.IS_ENTITY_PLAYING_ANIM || hash == Hash.HAS_ANIM_DICT_LOADED) value=true;
        else throw new Exception("Unexpected query: " + hash);
        return (T)value;
    }
    public static void Call(Hash hash, params object[] args) {
        Mutations++;
        if (hash == Hash.SET_ENTITY_ANIM_CURRENT_TIME) ((Ped)args[0]).Playhead = (float)args[3];
        else if (hash == Hash.TASK_PLAY_ANIM) ((Ped)args[0]).Outro = true;
        else if (hash != Hash.SET_ENTITY_ANIM_SPEED && hash != Hash.SET_ENTITY_COORDS_NO_OFFSET)
            throw new Exception("Unexpected mutation: " + hash);
    }
}
class Telemetry { public int Stops; public void SendStop() { Stops++; } }
class Harness {
    class ALifePedData { }
    private readonly Dictionary<string,ALifePedData> _aLifePeds = new Dictionary<string,ALifePedData>();
    private string _currentGirlKey;
    private ScriptState state = ScriptState.Animating;
    private MenuLevel menuLevel = MenuLevel.None;
    private Mode mode = Mode.Street;
    private int animPhase = 2, menuIndex, keyCooldown, _menuControlCooldown;
    private const int KEY_COOLDOWN_FRAMES = 12;
    private bool _finishExecutePending, _liveVoiceMenu, _suppressFinishUntilMasterReleased;
    private bool _usingController, tokenKeyboardOpen, _finishInside, _finishForced, _finishAsked;
    private bool _speechGapKeyboardOpen, _speechGapInputFrame;
    private ClubDancePhase _clubPhase = ClubDancePhase.Off;
    private bool _finishInsideFreePass, _kissingReverse = true, _streetSitPropActive = true;
    private int _finishExecuteAt, _aLifeFinishInsidePrice, streetActionIdx, _lastRumbleTime;
    private bool _rumblePulseActive, _finishBurstFired, aLifeMode;
    private string currentAction = "sex", currentMaleDict = "male_dict", currentMaleAnim = "male_loop";
    private string currentFemaleDict = "female_dict", currentFemaleAnim = "female_loop";
    private float animSpeed = 1.0f;
    private float _femaleAnimSpeedScale=1f;
    private bool _standingBjReverse,_rdoggyReverse;
    private int animWaitTime;
    private readonly Keys masterKey = Keys.J, menuBackKey = Keys.Back, menuSelectKey=Keys.NumPad5;
    private int masterControlModifier = 2, masterControl = 1, menuBackControl = 3,menuSelectControl=4;
    private readonly Ped girl = new Ped();
    private readonly Ped player = new Ped();
    private readonly Telemetry _telemetry = new Telemetry();
    private bool GeneralHandlerReached;
    private readonly List<string> DrawnItems = new List<string>();
    private void DrawSectionHeader(string text,float x,ref float y) { }
    private void DrawMenuItem(string text,int index,float x,ref float y,float lh) { DrawnItems.Add(text); }
    private void SetVibration(ushort left,ushort right) { }
    private void ShowHudStatus(string text,int time) { }
    private bool RequestAnimDict(string dict) { return true; }
    private void GetStreetAnimData(int action,out string md,out string ma,out string fd,out string fa,
        out Vector3 off,out float hd,out bool sit,out float zo,out float rx) {
        md=currentMaleDict;ma=currentMaleAnim;fd=currentFemaleDict;fa=currentFemaleAnim;
        off=new Vector3();hd=0;sit=false;zo=0;rx=0;
    }
    private void GetStreetPropIntroExitAnimData(int phase,int action,out string md,out string ma,
        out string fd,out string fa,out Vector3 off,out float hd,out bool sit,out float zo,out float rx,out float rh) {
        md="md";ma="ma";fd="fd";fa="fa";off=new Vector3();hd=0;sit=true;zo=0;rx=0;rh=0;
    }
'''

tests = r'''
    private static int count;
    private static void Check(bool value,string name) { count++; if (!value) throw new Exception("FAIL: " + name); }
    private void Step(bool held) {
        Game.Player.Character=player;player.Handle=1;girl.Handle=2;
        if (keyCooldown>0) keyCooldown--;
        Game.Held=held; Function.MasterHeld=held; Function.MasterPressed=held && !previousHeld;
        previousHeld=held;
        SampleKeyboardMasterInput();
        PollMasterRelease(); TickMasterInput();
    }
    private bool previousHeld;
    public static void Main() {
        foreach (Mode testMode in new[]{ Mode.Car,Mode.Street }) {
            foreach (int phase in new[]{0,1,3,4,100}) {
                var h=new Harness();h.mode=testMode;h.animPhase=phase;
                int mutations=Function.Mutations;h.Step(true);
                Check(h.menuLevel==MenuLevel.None && h.animPhase==phase && !h._finishExecutePending
                    && Function.Mutations==mutations,"J ignores transition/intro phase " + phase + " in " + testMode);
                h.animPhase=2;
                for(int frame=0;frame<30;frame++)h.Step(true);
                Check(h.menuLevel==MenuLevel.None && !h._finishExecutePending,"held intro press cannot finish when loop starts");
                h.Step(false);h.keyCooldown=0;h.Step(true);
                Check(h.menuLevel==MenuLevel.Finish && h.animPhase==2 && !h._finishExecutePending,"release and repress opens Finish after intro");
            }
        }
        foreach (string action in new[]{"sex","blowjob","kissing","facesitting"}) {
            var h=new Harness();h.currentAction=action;
            int mutations=Function.Mutations;h.Step(true);
            Check(h.menuLevel==MenuLevel.Finish && h.animPhase==2 && !h._finishExecutePending
                && Function.Mutations==mutations,"J opens overlay without changing either actor for " + action);
            for(int frame=0;frame<60;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.Finish && !h._finishExecutePending && Function.Mutations==mutations,"holding J cannot repeat/finish " + action);
            h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.J});
            Check(!h.GeneralHandlerReached && h.menuLevel==MenuLevel.Finish,"keyboard event/repeat cannot invoke general close handler");
            h.BackFromFinish();
            Check(h.menuLevel==MenuLevel.None && h.animPhase==2 && !h._finishExecutePending && Function.Mutations==mutations,"Back preserves loop without finishing");
        }
        foreach (bool controller in new[]{false,true}) {
            var h=new Harness();h._usingController=controller;
            h.Step(true);
            Check(h.menuLevel==MenuLevel.Finish && !h._finishExecutePending,"master input opens Finish for keyboard/controller");
            h.Step(false);h.keyCooldown=0;h.Step(true);
            Check(h.menuLevel==MenuLevel.None && !h._finishExecutePending && h.animPhase==2,"second press closes Finish without stopping loop");
        }
        {
            var h=new Harness();h._usingController=true;h.menuLevel=MenuLevel.Finish;
            Function.MasterHeld=true;Function.MasterPressed=true;Function.BackPressed=false;
            h.HandleControllerMenuInput();
            Check(!h.GeneralHandlerReached && h.menuLevel==MenuLevel.Finish,"controller master combo bypasses general menu-close handler");
        }
        {
            var h=new Harness();h._finishExecutePending=true;h.Step(true);
            Check(h.menuLevel==MenuLevel.None && h._finishExecutePending,"J does not reopen Finish during already scheduled finish");
            h=new Harness();h._liveVoiceMenu=true;h.menuLevel=MenuLevel.PartnerVoices;
            h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.J});
            Check(!h._liveVoiceMenu && h.menuLevel==MenuLevel.None && h._suppressFinishUntilMasterReleased,"live voice close consumes J without opening Finish");
        }
        foreach(string action in new[]{"kissing","facesitting"}) {
            var h=new Harness();h.currentAction=action;h.streetActionIdx=action=="kissing"?0:1;
            Check(h.FinishOptionCount()==1,"simple actions have one explicit Finish option");
            float y=0;h.DrawFinishMenu(0,ref y,0.034f);
            Check(h.DrawnItems.Count==1 && h.DrawnItems[0]=="Finish","simple menu draws one finish row");
            int mutations=Function.Mutations;h.Step(true);h.ExecuteSimplePending(h.player);
            Check(h.animPhase==2 && !h._finishExecutePending && Function.Mutations==mutations,"simple action transition cannot run before selection");
            h.keyCooldown=0;h.OnKeyUp(null,new KeyEventArgs{KeyCode=Keys.NumPad5});h.SelectFinishChoice();
            Check(h._finishExecutePending && h.menuLevel==MenuLevel.None && h.animPhase==2 && Function.Mutations==mutations,"explicit simple Finish only schedules transition");
            h.ExecuteSimplePending(h.player);
            Check(!h._finishExecutePending && h.animPhase==3 && Function.Mutations>mutations,"simple transition begins only after explicit choice");
            Check(action=="kissing" ? h.player.Playhead==0.5f && h.girl.Playhead==0.5f : h.girl.Outro,
                "original special outro is preserved after choice");
        }
        foreach(int choice in new[]{0,1}) {
            var h=new Harness();h.currentAction="sex";h.menuLevel=MenuLevel.Finish;h.menuIndex=choice;
            Check(h.FinishOptionCount()==2,"sandbox retains two normal Finish choices");
            h.SelectFinishChoice();
            Check(h._finishExecutePending && h._finishInside==(choice==1) && h.menuLevel==MenuLevel.None,"normal Finish choice schedules requested option");
        }
        Console.WriteLine("PASS: " + count + " J/Finish assertions; GTA natives mocked, no in-game animation validation.");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-finish-tests-') as directory:
    temp = Path(directory)
    cs = temp / 'FinishTests.cs'
    dll = temp / 'FinishTests.dll'
    cs.write_text(mocks + version_declaration + master_input + street_protection + simple + master + close_live + keyboard + controller + poll_release
                  + tick + select + options + draw + pending_guard + back + tests)
    rsp = temp / 'refs.rsp'
    rsp.write_text('\n'.join('/r:' + str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet), str(sdk), '/nologo', '/target:exe', '/langversion:5', '/nostdlib+',
                    '@' + str(rsp), '/out:' + str(dll), str(cs)], check=True)
    (temp / 'FinishTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net8.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': runtime}}}))
    subprocess.run([str(dotnet), str(dll)], cwd=temp, check=True)
