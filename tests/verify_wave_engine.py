#!/usr/bin/env python3
"""Exercise the actual managed waveOut engine with a deterministic native backend.

Usage: python3 tests/verify_wave_engine.py [dotnet] [source]
This verifies parsing, native buffer lifetime, independent clips and cleanup.
It does not exercise Windows waveOut drivers or establish audible playback.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
dotnet = Path(sys.argv[1] if len(sys.argv) > 1 else
              shutil.which('dotnet') or '/workspace/tools/csharp/dotnet/dotnet').resolve()
source = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'Mod/scripts/CinnamonCoffee.3.cs'
text = source.read_text(encoding='utf-8-sig')
engine = text[text.index('// PCM WAVE OUTPUT'):text.index('// END PCM WAVE OUTPUT')]
sdk = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name

harness = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
namespace CinnamonCoffee {
class WaveTests {
    class Device {
        public IntPtr Header; public PcmWaveMixer.WaveFormat Format;
        public bool Prepared, Submitted, Done; public double Started;
    }
    class Fake : PcmWaveMixer.IWaveOutApi {
        public Dictionary<IntPtr,Device> Devices = new Dictionary<IntPtr,Device>();
        public List<byte[]> Played = new List<byte[]>();
        public List<PcmWaveMixer.WaveFormat> Formats = new List<PcmWaveMixer.WaveFormat>();
        public string Fail = ""; public int Opens, Closes, Resets, Writes, Unprepares; public double Time;
        private int next;
        bool Failure(string operation) { if(Fail!=operation)return false; Fail="";return true; }
        void Header(Device d, uint extra) {
            var h=(PcmWaveMixer.WaveHeader)Marshal.PtrToStructure(d.Header,typeof(PcmWaveMixer.WaveHeader));
            h.Flags|=extra;Marshal.StructureToPtr(h,d.Header,false);
        }
        public uint Open(out IntPtr device, ref PcmWaveMixer.WaveFormat format) {
            if(Failure("open_bad_handle")){device=new IntPtr(999);return 2;}
            device=IntPtr.Zero;if(Failure("open"))return 2;
            device=new IntPtr(++next);Devices.Add(device,new Device { Format=format });Opens++;return 0;
        }
        public uint Prepare(IntPtr device, IntPtr header,uint size) {
            if(size!=Marshal.SizeOf(typeof(PcmWaveMixer.WaveHeader)))throw new Exception("ABI header size");
            var d=Devices[device];d.Header=header;if(Failure("prepare"))return 3;
            d.Prepared=true;Header(d,2);return 0;
        }
        public uint Write(IntPtr device,IntPtr header,uint size) {
            var d=Devices[device];if(!d.Prepared)throw new Exception("write without prepare");
            if(Failure("write"))return 4;
            var h=(PcmWaveMixer.WaveHeader)Marshal.PtrToStructure(header,typeof(PcmWaveMixer.WaveHeader));
            var bytes=new byte[h.Length];Marshal.Copy(h.Data,bytes,0,bytes.Length);
            Played.Add(bytes);Formats.Add(d.Format);d.Submitted=true;d.Started=Time;Writes++;Header(d,16);return 0;
        }
        public uint Reset(IntPtr device) {
            Resets++;if(Failure("reset"))return 5;
            var d=Devices[device];d.Done=true;Header(d,1);return 0;
        }
        public uint Unprepare(IntPtr device,IntPtr header,uint size) {
            var d=Devices[device];Unprepares++;
            if(Failure("unprepare"))return 33;
            if(d.Submitted&&!d.Done)return 33;
            // The engine must keep header and PCM memory valid up to successful unprepare.
            var h=(PcmWaveMixer.WaveHeader)Marshal.PtrToStructure(header,typeof(PcmWaveMixer.WaveHeader));
            if(h.Data==IntPtr.Zero||h.Length==0)throw new Exception("prematurely freed PCM");
            Marshal.ReadByte(h.Data);d.Prepared=false;return 0;
        }
        public uint Close(IntPtr device) {
            var d=Devices[device];if(d.Prepared)throw new Exception("close before unprepare");
            if(Failure("close"))return 6;
            Devices.Remove(device);Closes++;return 0;
        }
        public void Advance(double ms) {
            Time+=ms;
            foreach(var d in Devices.Values)if(d.Submitted&&!d.Done) {
                var h=(PcmWaveMixer.WaveHeader)Marshal.PtrToStructure(d.Header,typeof(PcmWaveMixer.WaveHeader));
                if(Time-d.Started>=1000.0*h.Length/d.Format.AverageBytesPerSecond){d.Done=true;Header(d,1);}
            }
        }
    }
    static int count;
    static void Check(bool condition,string message){count++;if(!condition)throw new Exception("FAIL: "+message);}
    static byte[] Wav(int ms=400,bool junk=false,bool dataFirst=false) {
        byte[] pcm=new byte[22000*2*ms/1000];for(int i=0;i<pcm.Length;i++)pcm[i]=(byte)(i%127);
        using(var s=new MemoryStream())using(var w=new BinaryWriter(s)) {
            w.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));w.Write(0);w.Write(System.Text.Encoding.ASCII.GetBytes("WAVE"));
            if(junk){w.Write(System.Text.Encoding.ASCII.GetBytes("JUNK"));w.Write(3);w.Write(new byte[]{7,8,9,0});}
            if(dataFirst){w.Write(System.Text.Encoding.ASCII.GetBytes("data"));w.Write(pcm.Length);w.Write(pcm);}
            w.Write(System.Text.Encoding.ASCII.GetBytes("fmt "));w.Write(16);w.Write((ushort)1);w.Write((ushort)1);
            w.Write(22000);w.Write(44000);w.Write((ushort)2);w.Write((ushort)16);
            if(!dataFirst){w.Write(System.Text.Encoding.ASCII.GetBytes("data"));w.Write(pcm.Length);w.Write(pcm);}
            w.Flush();long size=s.Length;s.Position=4;w.Write((uint)(size-8));w.Flush();return s.ToArray();
        }
    }
    public static void Main(string[] args) {
        Check(Marshal.SizeOf(typeof(PcmWaveMixer.WaveFormat))==18,"WAVEFORMATEX is packed 18 bytes");
        Check(Marshal.SizeOf(typeof(PcmWaveMixer.WaveHeader))==(IntPtr.Size==8?48:32),"WAVEHDR native pointer alignment");
        Check(Marshal.OffsetOf(typeof(PcmWaveMixer.WaveHeader),"Flags").ToInt32()==(IntPtr.Size==8?24:16),"WAVEHDR flags offset");
        var api=new Fake();var mixer=new PcmWaveMixer(api,8);byte[] wave=Wav();
        Check(mixer.Play(wave,"slap"),"first 400ms effect starts");
        api.Advance(180);Check(mixer.Play(wave,"slap"),"second effect starts at 180ms without serial wait");
        Check(mixer.ActiveCount==2&&api.Resets==0,"overlapping complete effects retain separate devices");
        Check(mixer.Play(wave,"bj")&&mixer.Play(wave,"kiss"),"other channels start independently");
        Check(mixer.IsPlaying("bj")&&mixer.IsPlaying("slap")&&mixer.IsPlaying("kiss"),"all channels report active");
        api.Advance(220);mixer.Tick();
        Check(mixer.ActiveCount==3&&api.Closes==1,"first clip closes only after its full 400ms");
        Check(api.Resets==0,"natural completion never resets any live device");
        mixer.Stop("bj");Check(!mixer.IsPlaying("bj")&&mixer.IsPlaying("slap")&&mixer.IsPlaying("kiss"),"targeted stop leaves other channels playing");
        Check(api.Resets==1,"only selected channel reset");
        api.Advance(180);mixer.Tick();Check(mixer.ActiveCount==0&&api.Devices.Count==0,"all completed clips unprepared and closed");
        Check(api.Opens==api.Closes,"every opened device released");
        Check(api.Played[0].Length==17600&&api.Played[1].Length==17600,"entire PCM buffers submitted; no clipping");
        Check(api.Played[0][127]==0&&api.Played[1][128]==1,"PCM content preserved in every overlapping clip");

        api=new Fake();mixer=new PcmWaveMixer(api,2);
        Check(mixer.Play(wave,"slap")&&mixer.Play(wave,"slap"),"voice cap filled");
        Check(!mixer.Play(wave,"bj")&&api.Resets==0&&api.Opens==2,"cap skips new clip rather than stealing one");
        api.Advance(400);Check(mixer.Play(wave,"bj"),"completed voices reclaimed before cap check");
        mixer.Dispose();Check(mixer.ActiveCount==0&&api.Devices.Count==0,"dispose resets and releases every remaining voice");
        Check(!mixer.Play(wave,"slap"),"disposed engine cannot start audio");
        mixer.Dispose();Check(mixer.ActiveCount==0,"dispose is idempotent");

        api=new Fake();mixer=new PcmWaveMixer(api,8);
        Check(mixer.Play(Wav(400,true),"slap"),"odd metadata chunk skipped with padding");
        Check(mixer.Play(Wav(400,false,true),"bj"),"data before fmt parsed safely");
        mixer.Dispose();
        Check(!mixer.Play(wave,"other"),"unknown channel rejected");
        api=new Fake();mixer=new PcmWaveMixer(api,8);
        Check(!mixer.Play(null,"bj")&&!mixer.Play(new byte[44],"bj"),"null and invalid RIFF rejected");
        Check(!mixer.Play(wave,"slap",0)&&!mixer.Play(wave,"slap",float.NaN)&&!mixer.Play(wave,"slap",float.PositiveInfinity),"invalid rates rejected");
        Check(!mixer.Play(wave,"other"),"unknown channel does not reach native API");
        byte[] bad=(byte[])wave.Clone();bad[4]=255;bad[5]=255;bad[6]=255;bad[7]=255;
        Check(!mixer.Play(bad,"bj"),"oversized RIFF rejected before allocation");
        bad=(byte[])wave.Clone();bad[32]=3;Check(!mixer.Play(bad,"bj"),"invalid block alignment rejected");
        bad=(byte[])wave.Clone();bad[28]=1;Check(!mixer.Play(bad,"bj"),"inconsistent byte rate rejected");
        bad=(byte[])wave.Clone();bad[20]=3;Check(!mixer.Play(bad,"bj"),"non-PCM format rejected");
        bad=(byte[])wave.Clone();bad[22]=8;Check(!mixer.Play(bad,"bj"),"unsupported channel count rejected");
        Check(api.Opens==0,"malformed WAVs do not open native devices");
        Check(mixer.Play(wave,"slap",2f),"runtime playback rate accepted without changing file");
        Check(api.Formats[0].SamplesPerSecond==44000&&api.Formats[0].AverageBytesPerSecond==88000,"native format rate scales consistently");
        Check(api.Played[0].Length==17600&&wave[24]==240,"rate preserves every PCM byte and original WAV header");
        api.Advance(199);mixer.Tick();Check(mixer.ActiveCount==1,"faster playback retains buffer until complete");
        api.Advance(1);mixer.Tick();Check(mixer.ActiveCount==0,"runtime 2x playback completes full clip in 200ms");

        foreach(string operation in new[]{"open","open_bad_handle","prepare","write"}) {
            api=new Fake { Fail=operation };mixer=new PcmWaveMixer(api,8);
            Check(!mixer.Play(wave,"bj"),operation+" failure reported");
            Check(mixer.LastError!=0,operation+" failure preserves MMRESULT");
            Check(mixer.ActiveCount==0&&api.Devices.Count==0,operation+" failure releases allocation/device");
        }
        api=new Fake();mixer=new PcmWaveMixer(api,8);mixer.Play(wave,"bj");api.Fail="reset";
        mixer.Stop("bj");Check(mixer.ActiveCount==1&&api.Devices.Count==1,"failed reset retains driver-owned memory");
        mixer.Tick();Check(mixer.ActiveCount==0&&api.Devices.Count==0,"retry releases reset-failed clip safely");
        api=new Fake();mixer=new PcmWaveMixer(api,8);mixer.Play(wave,"bj");api.Advance(400);api.Fail="unprepare";
        mixer.Tick();Check(mixer.ActiveCount==1&&api.Devices.Count==1,"WAVERR_STILLPLAYING retains native buffer");
        mixer.Tick();Check(mixer.ActiveCount==0&&api.Devices.Count==0,"later unprepare success releases completed buffer");
        api=new Fake();mixer=new PcmWaveMixer(api,8);mixer.Play(wave,"bj");api.Advance(400);api.Fail="close";
        mixer.Tick();Check(mixer.ActiveCount==1&&api.Devices.Count==1,"failed close retains device for retry");
        mixer.Tick();Check(mixer.ActiveCount==0&&api.Devices.Count==0,"close retry releases device after buffer cleanup");
        api=new Fake();mixer=new PcmWaveMixer(api,8);
        for(int i=0;i<200;i++){Check(mixer.Play(wave,"slap"),"repeated clip "+i);api.Advance(400);mixer.Tick();}
        Check(api.Opens==api.Closes&&mixer.ActiveCount==0,"repeated effects do not accumulate active native devices");
        int actualClips = 0;
        foreach(string path in Directory.GetFiles(args[0], "*.wav")) {
            api = new Fake(); mixer = new PcmWaveMixer(api, 8);
            Check(mixer.Play(File.ReadAllBytes(path), "slap"), "actual uploaded PCM accepted: " + Path.GetFileName(path));
            Check(api.Played.Count == 1 && api.Played[0].Length > 0, "entire uploaded PCM submitted");
            mixer.Dispose();
            Check(api.Devices.Count == 0 && mixer.ActiveCount == 0, "uploaded PCM lifecycle cleanup");
            actualClips++;
        }
        Check(actualClips == 31, "all 31 uploaded WAVs exercised through the actual parser/backend lifecycle");
        Console.WriteLine("PASS: "+count+" waveOut engine assertions; managed native backend simulated, Windows driver/audio not run.");
    }
}}
'''

# C# using clauses must precede both the inserted namespace and test namespace.
prefix = 'using System;\nusing System.Collections.Generic;\nusing System.Runtime.InteropServices;\n'
# The harness's own usings precede the engine; concatenate only once.
using_end = harness.index('namespace CinnamonCoffee')
combined = harness[:using_end] + engine + '\n' + harness[using_end:]
with tempfile.TemporaryDirectory(prefix='cinnamon-wave-tests-') as directory:
    temp = Path(directory)
    cs = temp / 'WaveTests.cs'
    dll = temp / 'WaveTests.dll'
    cs.write_text(combined)
    rsp = temp / 'refs.rsp'
    rsp.write_text('\n'.join('/r:' + str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet), str(sdk), '/nologo', '/target:exe', '/langversion:5', '/nostdlib+',
                    '@' + str(rsp), '/out:' + str(dll), str(cs)], check=True)
    (temp / 'WaveTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net8.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': runtime}}}))
    subprocess.run([str(dotnet), str(dll), str(ROOT / 'Mod/scripts/CinnamonCoffeeSounds')], check=True)
