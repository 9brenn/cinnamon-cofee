#!/usr/bin/env python3
"""Exercise extracted GTA audio/menu methods with adversarial engine responses.

Requires the .NET 8 SDK; accepts an optional path to dotnet. Compilation against
real SHVDN/.NET Framework is a separate check. These tests distinguish launch requests from simulated accepted playback, and
exercise diagnostic hash mismatches, rejected or late starts, and flag gaps.
The PcmWaveMixer boundary is simulated here; its WinMM lifecycle is tested in
verify_wave_engine.py. GTA V is not run and in-game audibility is not established.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source_path = Path(sys.argv[2]) if len(sys.argv)>2 else ROOT / 'Mod/scripts/CinnamonCoffee.3.cs'
source = source_path.read_text(encoding='utf-8-sig')
selector = source.split('// PARTNER VOICE SELECTION', 1)[1].split('// END PARTNER VOICE SELECTION', 1)[0]
masked = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:[^"]|"")*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),source)
def method(signature):
    start=source.index(signature);brace=masked.index('{',start);depth=1;end=brace+1
    while depth:
        if masked[end]=='{':depth+=1
        elif masked[end]=='}':depth-=1
        end+=1
    return source[start:end]
methods = '\n'.join(method(signature) for signature in (
    'private void AssignHookerVoice(Ped ped)',
    re.search(r'private (?:void|bool) PlayPedSpeech\(Ped ped, string speechName\)',source).group(0),
    re.search(r'private (?:void|bool) PlayMoaningSounds\(\)',source).group(0),
    'private void TickPostSexVoice()',
    'private void TickCustomSound()',
    'private bool PlayBjCustom(string path, bool force = false)',
    'private void PlaySlapSound(string path)',
    'private void PlayKissSound(string path)',
))
voices = 'private static readonly string[] HOOKER_VOICES = {' + source.split('private static readonly string[] HOOKER_VOICES = {', 1)[1].split('};', 1)[0] + '};'
finish_condition = source.split('if (masterTriggered && keyCooldown == 0 && !_liveVoiceMenu', 1)[1].split(')', 1)[0]
finish_gate = 'private bool TestFinishGate(bool masterTriggered) { return masterTriggered && keyCooldown == 0 && !_liveVoiceMenu' + finish_condition + '; }'
periodic = 'private void TickPeriodic() {' + source.split('// Animation speed controls request cadence, never the duration of a speech line.', 1)[1].split('// Custom BJ sounds', 1)[0] + '}\n'
effects = 'private void TickEffects() { int now=Game.GameTime; '+source.split('// Sex slap sounds —',1)[1].split('// Slow healing during loop phase',1)[0].split('bool _standingFinishInsideSlap',1)[1]+'}'
effects=effects.replace(' { int now=Game.GameTime; ',' { int now=Game.GameTime; bool _standingFinishInsideSlap',1)
# Wiring checks supplement executable tests, because complete game input methods
# involve hundreds of unrelated calls and cannot run outside the game.
wiring = {
    'keyboard closes overlay before normal navigation': 'if (_liveVoiceMenu && (e.KeyCode == menuBackKey || e.KeyCode == masterKey))\n            { CloseLiveVoiceMenu(); return; }',
    'controller closes overlay': 'if (_liveVoiceMenu && (Function.Call<bool>(Hash.IS_DISABLED_CONTROL_JUST_PRESSED, 0, menuBackControl)',
    'overlay suppresses finish trigger': 'if (masterTriggered && keyCooldown == 0 && !_liveVoiceMenu && !_suppressFinishUntilMasterReleased)',
    'overlay suppresses animation speed buttons': 'speedCooldown == 0 && !_finishExecutePending && !_liveVoiceMenu',
    'periodic voice reapply observes speech': 'Game.GameTime >= _voiceReapplyAt && !IsPartnerSpeechBusy(girl) && !_pendingPartnerVoiceChange',
    'tick drives scheduler': 'TickPartnerAudio(); // Apply a requested voice only between complete speech lines.',
    'tick polls menu hotkey': 'PollLiveVoiceMenuToggle();',
    'full reset cancels pending audio': 'ResetPartnerAudio();\n            _girlCurrentVoice     = null;',
    'BJ scheduling observes own channel': 'if (now - _lastBjSoundTime > bjInterval && !_waveMixer.IsPlaying("bj") && _queuedCustomSoundPath == null)',
}
bj_producer=source.split('// Custom BJ sounds',1)[1].split('// Sex slap sounds',1)[0]
assert 'IsPartnerSpeechBusy' not in bj_producer, 'native speech must not gate normal WAV producer'
assert 'System.Media.SoundPlayer' not in source, 'global SoundPlayer path must not return'
for label, text in wiring.items():
    assert text in source, label

dotnet = Path(sys.argv[1] if len(sys.argv) > 1 else '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name
mocks = r'''
using System;
using System.Collections.Generic;
using System.IO;
enum Keys { F6, J }
namespace GTA { enum Control { FrontendY } }
class Model { public int Hash; }
class Ped {
    public int Handle; public bool Valid = true; public Model Model = new Model();
    public string Voice = ""; public int SpeakingUntil, VisibleFrom;
    public bool Exists() { return Valid; }
}
static class Game {
    public static int GameTime = 1000; public static bool KeyDown, MasterDown;
    public static bool IsKeyPressed(Keys key) { return key==Keys.F6 ? KeyDown : MasterDown; }
}
enum Hash : ulong {
    GET_HASH_KEY = 1, SET_AMBIENT_VOICE_NAME, SET_AUDIO_FLAG,
    PLAY_PED_AMBIENT_SPEECH_NATIVE, IS_DISABLED_CONTROL_PRESSED,
    IS_DISABLED_CONTROL_JUST_PRESSED, STOP_CURRENT_PLAYING_AMBIENT_SPEECH
}
static class Function {
    public static int Duration = 5000, Delay, VoiceSets, Stops, FalseFrom, FalseUntil, VoiceSetFailures;
    public static bool Modifier, ControllerY, MasterControl, AnySpeechAlways, WrongVoiceHash, RejectEveryLaunch;
    // Launch requests and simulated accepted starts are deliberately separate.
    public static List<string> Spoken = new List<string>();
    public static List<string> RequestedBanks = new List<string>();
    public static List<int> RequestTimes = new List<int>(), StartTimes = new List<int>();
    public static List<string> SpeechParameters = new List<string>();
    public static List<bool> DirectorFlags=new List<bool>();
    public static uint Key(string name) {
        uint value = 0;
        foreach (char c in name.ToLowerInvariant()) {
            value += c; value += value << 10; value ^= value >> 6;
        }
        value += value << 3; value ^= value >> 11; value += value << 15;
        return value;
    }
    public static void Reset() {
        Spoken.Clear(); SpeechParameters.Clear(); DirectorFlags.Clear(); RequestedBanks.Clear(); RequestTimes.Clear(); StartTimes.Clear(); AnySpeechAlways=WrongVoiceHash=RejectEveryLaunch=false; Duration=5000; Delay=VoiceSets=Stops=FalseFrom=FalseUntil=VoiceSetFailures=0; Modifier=ControllerY=false;
        Game.GameTime=1000; Game.KeyDown=Game.MasterDown=false; MasterControl=false;
    }
    public static void Call(Hash native, params object[] args) {
        if(native==Hash.SET_AUDIO_FLAG && (string)args[0]=="IsDirectorModeActive") DirectorFlags.Add((bool)args[1]);
        else if (native == Hash.SET_AMBIENT_VOICE_NAME) { if(VoiceSetFailures>0) VoiceSetFailures--; else ((Ped)args[0]).Voice = (string)args[1]; VoiceSets++; }
        else if (native == Hash.STOP_CURRENT_PLAYING_AMBIENT_SPEECH) { Stops++; ((Ped)args[0]).SpeakingUntil=0; }
        else if ((ulong)native == 0x3523634255FC3318UL || native == Hash.PLAY_PED_AMBIENT_SPEECH_NATIVE) {
            Ped ped=(Ped)args[0];
            RequestTimes.Add(Game.GameTime);
            RequestedBanks.Add((ulong)native==0x3523634255FC3318UL ? (string)args[2] : "");
            if(!RejectEveryLaunch) { ped.VisibleFrom=Game.GameTime+Delay; ped.SpeakingUntil=ped.VisibleFrom+Duration; StartTimes.Add(ped.VisibleFrom); }
            Spoken.Add((string)args[1]); SpeechParameters.Add((string)args[(ulong)native==0x3523634255FC3318UL ? 3 : 2]);
        }
    }
    public static T Call<T>(Hash native, params object[] args) {
        object value;
        if (native == Hash.GET_HASH_KEY) {
            uint hash = Key((string)args[0]); value = typeof(T) == typeof(uint) ? (object)hash : (object)unchecked((int)hash);
        } else if ((ulong)native == 0x5E203DA2BA15D436UL) value = Key(WrongVoiceHash ? "UNRELIABLE_READBACK" : ((Ped)args[0]).Voice);
        else if ((ulong)native == 0x729072355FA39EC9UL || (ulong)native == 0x9072C8B49907BFADUL) {
            Ped ped=(Ped)args[0]; value=((ulong)native==0x729072355FA39EC9UL && AnySpeechAlways) || (Game.GameTime>=ped.VisibleFrom && Game.GameTime<ped.SpeakingUntil && !(Game.GameTime>=FalseFrom && Game.GameTime<FalseUntil));
        } else if (native == Hash.IS_DISABLED_CONTROL_PRESSED) value=(int)args[1]==1 ? Modifier : MasterControl;
        else if (native == Hash.IS_DISABLED_CONTROL_JUST_PRESSED) value=ControllerY;
        else throw new Exception("Unexpected native: " + native);
        return (T)value;
    }
}
// Engine boundary only: actual WinMM/PcmWaveMixer lifecycle has its own tests.
class PcmWaveMixer {
    public class Clip { public string Channel; public int Start,Until;public float Rate; }
    public List<Clip> Clips=new List<Clip>();public int Stops;
    public bool Play(byte[] data,string channel,float rate=1f) { Clips.Add(new Clip{Channel=channel,Start=Game.GameTime,Until=Game.GameTime+400,Rate=rate});return true; }
    public bool IsPlaying(string channel) { return Clips.Exists(c=>c.Channel==channel && Game.GameTime<c.Until); }
    public void Tick() { }
    public void Stop(string channel) { Stops++; }
}
class CountingRandom : Random {
    public int GapDraws; public List<int> Gaps=new List<int>();
    public CountingRandom():base(42) { }
    public override int Next(int min,int max) {
        int value=base.Next(min,max);
        if(min==2000 && max>=5000 && max<=5001) { GapDraws++;Gaps.Add(value); }
        return value;
    }
}
class Harness {
    enum ScriptState { Idle, Approaching, Animating }
    enum Mode { Car,Street }
    enum MenuLevel { None, Main, PartnerVoices, Services }
    class ALifePedData { public string Voice; public int Reputation; }
    private static readonly Dictionary<int,string> voiceCache = new Dictionary<int,string>();
    private Dictionary<string,ALifePedData> _aLifePeds = new Dictionary<string,ALifePedData>();
    private CountingRandom rng = new CountingRandom();
    private Ped girl; private bool hasGirl=true, aLifeMode, sandboxMode=true;
    private int menuIndex, keyCooldown, _menuControlCooldown, _voiceReapplyAt;
    private const int KEY_COOLDOWN_FRAMES=12, VOICE_INTERVAL=7000;
    private string _girlCurrentVoice, hud, _currentGirlFp, _currentGirlKey;
    private bool _bjThroatPending, _throatSpeedLocked, _finishExecutePending, _usingController, tokenKeyboardOpen;
    private int _throatLockAt, _bjSoundBusyUntil;
    private int masterControlModifier=1, masterControl=2; private Keys masterKey=Keys.J;
    private int settingsSaved, aLifeSaved;
    private ScriptState state=ScriptState.Animating;
    private int animPhase=2;
    private float animSpeed=3.0f;
    private string currentAction="standing";
    private bool femaleMoanVoice=true, femaleEndVoice=true;
    private int lastVoiceTime, _postSexPhase, _postSexWaitUntil;
    private MenuLevel menuLevel=MenuLevel.None, _postSexPendingMenu=MenuLevel.None;
    private readonly PcmWaveMixer _waveMixer=new PcmWaveMixer();
    private Dictionary<string,byte[]> _bjWavData=new Dictionary<string,byte[]>();
    private Dictionary<string,int> _soundDurations=new Dictionary<string,int>();
    private bool slapSoundsEnabled=true,_finishInside;private Mode mode=Mode.Street;private int streetActionIdx=5,_lastSlapSoundTime,_lastKissSoundTime;
    private string[] _sexSlapFiles=new[]{"clip"},_kissSoundFiles=new[]{"clip"};
    private void ReportWavePlaybackError() { throw new Exception("unexpected simulated mixer failure"); }
    private void GetSlapIntervals(out int slow,out int mid,out int fast) { slow=600;mid=350;fast=180; }
    private string GetPedFingerprint(Ped ped) { return "FP" + ped.Handle; }
    private string ALifeKey(string fp) { return "AL:" + fp; }
    private bool IsProstHookerModel(Ped ped) { return false; }
    private ALifePedData GetOrCreateALifeData(Ped ped) {
        string key=ALifeKey(GetPedFingerprint(ped)); ALifePedData value;
        if (!_aLifePeds.TryGetValue(key,out value)) _aLifePeds[key]=value=new ALifePedData();
        return value;
    }
    private ALifePedData GetOrCreateProstALifeData(Ped ped) { return GetOrCreateALifeData(ped); }
    private void SaveSettings() { settingsSaved++; }
    private void SaveALife() { aLifeSaved++; }
    private void ShowHudStatus(string text,int time) { hud=text; }
    private void DrawSectionHeader(string text,float x,ref float y) { }
    private void DrawMenuText(string text,float x,float y,float w,float size,bool center,int r,int g,int b,int a) { }
    private void DrawMenuItem(string text,int index,float x,ref float y,float lh,float scale=0.31f) { }
'''
tests = r'''
    static int count,failures;
    static void Check(bool condition,string message) { count++; if(!condition) { failures++;Console.WriteLine("FAIL "+message); } }
    static void Run(Harness h,int first,int last,bool loops=true) {
        for(int t=first;t<=last;t+=50) { Game.GameTime=t; h.TickPartnerAudio(); if(loops) h.TickPeriodic(); }
    }
    static Harness New(bool native=false) {
        Function.Reset(); voiceCache.Clear(); var h=new Harness();
        h.girl=new Ped { Handle=42, Model=new Model { Hash=unchecked((int)Function.Key(native?"s_f_y_hooker_01":"a_f_y_bevhills_01")) } };
        h.girl.Voice=HOOKER_VOICES[2]; h.LoadPartnerVoiceCatalogue(); return h;
    }
    public static void Main() {
        var h=New();
        Check(h._partnerVoices.Count==8,"eight confirmed voice entries only");
        Check(NormalizePartnerVoice("S_F_Y_HOOKER_03_BLACK_FULL_02")==null,"unconfirmed bank excluded");
        Check(NormalizePartnerVoice("AMANDA")==null,"unrequested banks rejected");
        Check(NormalizePartnerVoice("  "+HOOKER_VOICES[0].ToLowerInvariant()+"  ")==HOOKER_VOICES[0],"valid IDs normalized");

        // A never-matching diagnostic hash must not prevent explicit-bank requests forever.
        h=New();Function.WrongVoiceHash=true;h.SelectPartnerVoice(HOOKER_VOICES[7]);Run(h,1000,15000);
        Check(Function.StartTimes.Count>0,"permanent voice hash mismatch cannot starve native requests for15seconds");
        Check(Function.RequestedBanks.Count>0 && Function.RequestedBanks.TrueForAll(v=>v==HOOKER_VOICES[7]),"explicit requested bank reaches native despite readback mismatch");
        Check(Function.RequestTimes.Count<20,"hash mismatch recovery does not generate per-frame launches");
        Check(h._voiceReadbackAttempts==3 && !h._voiceAwaitingReadback,"diagnostic hash readback stops after bounded three attempts");

        // IS_ANY_SPEECH_PLAYING may report unrelated/persistent state; no owned line exists here.
        h=New();Function.AnySpeechAlways=true;Run(h,1000,15000);
        Check(Function.StartTimes.Count>0,"unowned stuck ANY_SPEECH flag cannot cause minutes of silence");

        // Calls may be rejected by GTA without ever setting the actual ambient-speech flag.
        h=New();Function.RejectEveryLaunch=true;Run(h,1000,31000);
        Check(Function.StartTimes.Count==0 && Function.Spoken.Count>1,"rejected launches exercise retry path without simulating successful playback");
        Check(Function.RequestTimes.Count<=20,"rejected launch retries are bounded rather than every frame");
        Check(Function.RequestTimes.Count>1 && Function.RequestTimes[1]-Function.RequestTimes[0]<=5000,"rejected first launch recovers without fake full-line cooldown");
        Check(h.rng.GapDraws==0,"rejected starts never draw completed-line random gaps");

        // Accepted lines last5000ms. Their next request must follow actual completion by2–5s.
        h=New();h.SelectPartnerVoice(HOOKER_VOICES[0]);Run(h,1000,1500,false);Game.GameTime=2000;h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        int initialSets=Function.VoiceSets;
        Run(h,2050,6950);
        Check(Function.Spoken.Count==1 && Function.Stops==0,"5000ms accepted line stays whole at animation speed3");
        Check(Function.VoiceSets==initialSets,"active native line gets no bank reapply");
        Check(Function.DirectorFlags.Count==1 && Function.DirectorFlags[0],"interaction audio flag remains active across whole native line");
        for(int t=7000;t<=40000 && Function.StartTimes.Count<3;t+=50) { Game.GameTime=t;h.TickPartnerAudio();h.TickPeriodic(); }
        Check(Function.StartTimes.Count==3,"three complete accepted native lines are scheduled");
        for(int i=1;i<Function.StartTimes.Count;i++) {
            int gap=Function.StartTimes[i]-Function.StartTimes[i-1]-Function.Duration;
            Check(gap>=2000 && gap<=5050,"observed post-line gap remains2–5seconds independent of speed");
        }
        Check(h.rng.GapDraws==2,"exactly one randomized gap is drawn for each completed accepted line");
        Check(Function.SpeechParameters.Count>0 && Function.SpeechParameters.TrueForAll(v=>v=="SPEECH_PARAMS_ALLOW_REPEAT"),"native requests use non-forcing repeat parameters");

        h=New();h.PlayPedSpeech(h.girl,"GENERIC_HI");Run(h,1050,7000,false);
        int savedDue=h._nextPartnerLoopSpeechAt;int savedDraws=h.rng.GapDraws;
        Function.AnySpeechAlways=true;h.girl.VisibleFrom=7050;h.girl.SpeakingUntil=7350;Run(h,7050,7850,false);
        Check(savedDraws==1 && h.rng.GapDraws==savedDraws,"background-only speech cannot redraw completed-line gap");
        Check(h._nextPartnerLoopSpeechAt==savedDue,"background speech cannot postpone scheduled next line");

        h=New();h._bjSoundBusyUntil=200000;Run(h,1000,8000);
        Check(Function.StartTimes.Count>0,"native speech cadence never waits for WAV reservation");

        h=New();Function.Delay=400;h.PlayPedSpeech(h.girl,"GENERIC_HI");Game.GameTime=1350;h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        Check(Function.Spoken.Count==1,"delayed native startup cannot trigger overlapping second request");
        h=New();Function.Delay=1600;h.PlayPedSpeech(h.girl,"GENERIC_HI");Run(h,1050,12600);
        Check(h.rng.GapDraws==1,"late native acknowledgement still records one real completed line");
        Check(Function.RequestTimes.Count>=2 && Function.RequestTimes[1]-(1000+1600+Function.Duration)>=2000,"late-started full native line still receives post-line gap before next request");
        h=New(true);h.PlayPedSpeech(h.girl,"GENERIC_HI");initialSets=Function.VoiceSets;
        Function.FalseFrom=4000;Function.FalseUntil=4300;
        for(int t=3500;t<=4400;t+=50) {
            Game.GameTime=t;if(t==4100)h.SelectPartnerVoice(HOOKER_VOICES[7]);h.TickPartnerAudio();h.TickPeriodic();
        }
        Check(Function.Spoken.Count==1 && Function.VoiceSets==initialSets,"temporary speech flag gap cannot replace current line or bank");
        Run(h,4450,7000,false);
        Check(h.partnerVoice==HOOKER_VOICES[7] && h.girl.Voice==HOOKER_VOICES[7],"last pending bank applies after complete native line");
        h.SelectPartnerVoice("");Run(h,7050,8000,false);
        Check(h.girl.Voice==HOOKER_VOICES[2],"automatic restores captured native bank");

        h=New();h.aLifeMode=true;h.GetOrCreateALifeData(h.girl).Voice=HOOKER_VOICES[4];
        h.SelectPartnerVoice(HOOKER_VOICES[0]);Run(h,1000,1500,false);h.SelectPartnerVoice("");Run(h,1550,2500,false);
        Check(h.girl.Voice==HOOKER_VOICES[4] && h.GetOrCreateALifeData(h.girl).Voice==HOOKER_VOICES[4],"automatic preserves A-Life voice");
        h=New();voiceCache[42]=HOOKER_VOICES[5];h.SelectPartnerVoice(HOOKER_VOICES[0]);Run(h,1000,1500,false);h.SelectPartnerVoice("");Run(h,1550,2500,false);
        Check(h.girl.Voice==HOOKER_VOICES[5],"automatic preserves sandbox cache");

        h=New();h.PlayPedSpeech(h.girl,"GENERIC_HI");h.PlayPedSpeech(h.girl,"HOOKER_OFFER_SERVICE");h.PlayPedSpeech(h.girl,"HOOKER_OFFER_AGAIN");h.PlayPedSpeech(h.girl,"SEX_FINISHED");h.PlayPedSpeech(h.girl,"GENERIC_YES");h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        Check(h._queuedSpeechName=="SEX_FINISHED" && Function.Spoken.Count==1,"single pending important line retains finish priority");
        h._postSexPhase=1;h._postSexPendingMenu=MenuLevel.Services;
        for(int t=1050;t<=18000 && h._postSexPhase!=0;t+=50) { Game.GameTime=t;h.TickPartnerAudio();h.TickPostSexVoice(); }
        Check(Function.Spoken.Count>=3 && Function.Spoken[1]=="SEX_FINISHED" && Function.Spoken[2]=="HOOKER_OFFER_AGAIN" && h.menuLevel==MenuLevel.Services,"finish line stays before followup and deferred menu");
        h=New();h._bjThroatPending=true;h.PlayPedSpeech(h.girl,"SEX_GENERIC");h.PlayPedSpeech(h.girl,"SEX_FINISHED");h.TickPartnerAudio();
        Check(Function.Spoken.Count==1 && h.HasQueuedPartnerSpeech(),"native speech remains independent of custom throat audio locks");

        h=New();h._bjWavData["clip"]=new byte[16];h._soundDurations["clip"]=400;
        h.PlayPedSpeech(h.girl,"GENERIC_HI");h.PlaySlapSound("clip");
        Game.GameTime=1180;h.PlaySlapSound("clip");h.PlayKissSound("clip");
        Check(h._waveMixer.Clips.Count==3 && h._waveMixer.Stops==0,"slap and kiss wrappers launch during native speech without global stop");
        Check(h._waveMixer.Clips[0].Until==1400 && h._waveMixer.Clips[1].Start==1180 && h._waveMixer.Clips[1].Until==1580,"400ms slap clips can overlap180ms cadence without shortening either");
        Check(h.PlayBjCustom("clip"),"BJ wrapper ignores active slap/kiss/native channels");
        Game.GameTime=1250;Check(!h.PlayBjCustom("clip",true) && h._queuedCustomSoundPath=="clip","important BJ clip queues behind own channel only");
        h.TickCustomSound();Check(h._waveMixer.Clips.Count==4,"queued BJ waits own current clip");
        Game.GameTime=1580;h.TickCustomSound();Check(h._waveMixer.Clips.Count==5 && h._queuedCustomSoundPath==null && h._waveMixer.Stops==0,"queued BJ starts after its full own-channel duration without stopping other effects");
        h=New();h._bjWavData["clip"]=new byte[16];h._soundDurations["clip"]=400;
        h.PlaySlapSound("clip");h.PlayBjCustom("clip");h.PlayPedSpeech(h.girl,"GENERIC_HI");
        Check(Function.StartTimes.Count==1,"native request starts while independent WAV outputs are already playing");
        h=New();h._bjWavData["clip"]=new byte[16];h.currentAction="sex";h.animSpeed=1.5f;h.girl.SpeakingUntil=20000;
        for(int t=1000;t<=10000;t+=10) { Game.GameTime=t;h.TickEffects(); }
        int slowSlaps=h._waveMixer.Clips.Count;
        h=New();h._bjWavData["clip"]=new byte[16];h.currentAction="sex";h.animSpeed=3f;h.girl.SpeakingUntil=20000;
        for(int t=1000;t<=10000;t+=10) { Game.GameTime=t;h.TickEffects(); }
        Check(h._waveMixer.Clips.Count>slowSlaps,"actual slap producer starts more full clips at speed3 than1.5");
        Check(h._waveMixer.Clips.TrueForAll(c=>c.Rate==1f && c.Until-c.Start==400),"tempo controls effect start cadence while wrapper keeps full clip at original rate");

        h=New(); h.ToggleLiveVoiceMenu();
        Check(h._liveVoiceMenu && h.menuLevel==MenuLevel.PartnerVoices,"live overlay opens during loop");
        Check(h.state==ScriptState.Animating && h.animPhase==2 && h.animSpeed==3f,"opening overlay preserves state phase speed");
        h.ToggleLiveVoiceMenu();
        Check(!h._liveVoiceMenu && h.menuLevel==MenuLevel.None && h.state==ScriptState.Animating && h.animPhase==2 && h.animSpeed==3f,"closing overlay preserves animation");
        h.animPhase=1; h.ToggleLiveVoiceMenu(); Check(!h._liveVoiceMenu,"opening blocked during intro phase");
        h.animPhase=2; h._finishExecutePending=true; h.ToggleLiveVoiceMenu(); Check(!h._liveVoiceMenu,"opening blocked during pending finish");
        h._finishExecutePending=false; h.state=ScriptState.Idle; h.ToggleLiveVoiceMenu(); Check(!h._liveVoiceMenu,"opening blocked outside animation");
        h.state=ScriptState.Animating; h.tokenKeyboardOpen=true; Game.KeyDown=true; h.PollLiveVoiceMenuToggle();
        Check(!h._liveVoiceMenu,"voice hotkey ignored while token keyboard open");
        h.tokenKeyboardOpen=false; Game.KeyDown=false; h.PollLiveVoiceMenuToggle(); Game.KeyDown=true; h.PollLiveVoiceMenuToggle();
        Check(h._liveVoiceMenu,"F6 rising edge opens live overlay");
        h.PollLiveVoiceMenuToggle(); Check(h._liveVoiceMenu,"holding F6 does not retrigger");
        Game.KeyDown=false; h.PollLiveVoiceMenuToggle(); Game.KeyDown=true; h.PollLiveVoiceMenuToggle();
        Check(!h._liveVoiceMenu,"next F6 rising edge closes overlay");
        h._usingController=true; Function.Modifier=Function.ControllerY=true; h.PollLiveVoiceMenuToggle();
        Check(h._liveVoiceMenu,"controller modifier plus Y opens overlay");
        Function.ControllerY=false; h.animPhase=3; h.PollLiveVoiceMenuToggle();
        Check(!h._liveVoiceMenu,"loop exit closes overlay automatically");

        h=New(); h.ToggleLiveVoiceMenu(); Game.MasterDown=true; h.CloseLiveVoiceMenu();
        for(int frame=0;frame<40;frame++) {
            h.keyCooldown=Math.Max(0,h.keyCooldown-1); h.PollLiveVoiceMenuToggle();
            Check(!h.TestFinishGate(true),"holding J after menu close cannot finish at frame "+frame);
        }
        Game.MasterDown=false; h.PollLiveVoiceMenuToggle();
        Check(!h._suppressFinishUntilMasterReleased && h.TestFinishGate(true),"releasing J permits later fresh finish input");
        h=New(); h.ToggleLiveVoiceMenu(); h._usingController=true; Function.Modifier=Function.MasterControl=true; h.CloseLiveVoiceMenu();
        h.keyCooldown=0; h.PollLiveVoiceMenuToggle(); Check(!h.TestFinishGate(true),"controller close chord remains suppressed while held");
        Function.MasterControl=false; h.PollLiveVoiceMenuToggle(); Check(h.TestFinishGate(true),"controller master release clears finish suppression");
        h=New(); h.ToggleLiveVoiceMenu(); h.menuLevel=MenuLevel.Services; h.menuIndex=4; h.animPhase=3; h.PollLiveVoiceMenuToggle();
        Check(!h._liveVoiceMenu && h.menuLevel==MenuLevel.Services && h.menuIndex==4,"automatic close preserves a newer menu and cursor");

        h=New(); h.PlayPedSpeech(h.girl,"GENERIC_HI"); h.SelectPartnerVoice(HOOKER_VOICES[0]);
        h.PlayPedSpeech(h.girl,"SEX_FINISHED"); h.ToggleLiveVoiceMenu(); h.ResetPartnerAudio();
        Check(!h._pendingPartnerVoiceChange && !h.HasQueuedPartnerSpeech() && h._speechLaunchPedHandle==0 && !h._liveVoiceMenu,"reset cancels pending choice queue launch and overlay");
        h=New(); h.QueuePartnerSpeech(h.girl,"SEX_FINISHED"); h.girl=new Ped { Handle=99 }; h.TickPartnerAudio();
        Check(h._queuedSpeechName==null && Function.Spoken.Count==0,"stale queued speech not delivered to replacement partner");
        h=New(); h.QueuePartnerSpeech(h.girl,"SEX_FINISHED"); h.girl.Valid=false; h.TickPartnerAudio();
        Check(h._queuedSpeechName==null && !h._pendingPartnerVoiceChange,"lost partner cancels scheduled audio");
        Check(Function.Stops==0,"scheduler never stops ambient speech");
        Console.WriteLine("Native scheduler/menu: "+(count-failures)+" passed, "+failures+" failed. Launch requests are distinct from simulated playback; GTA not run.");
        if(failures>0)Environment.Exit(1);
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-audio-tests-') as directory:
    temp=Path(directory); cs=temp/'AudioTests.cs'; dll=temp/'AudioTests.dll'
    cs.write_text(mocks+voices+selector+methods+periodic+effects+'\n'.join(re.findall(r'private const int KISS_SOUND_\w+\s*=\s*\d+;',source))+finish_gate+tests)
    rsp=temp/'refs.rsp'; rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/nowarn:0649,0414,0169','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'AudioTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
print('PASS: '+str(len(wiring))+' input/reset/audio wiring checks.')
