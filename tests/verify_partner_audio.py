#!/usr/bin/env python3
"""Exercise extracted real GTA audio/menu methods with deterministic native mocks.

Requires the .NET 8 SDK; accepts an optional path to dotnet. Compilation against
real SHVDN/.NET Framework is a separate check. These tests do not run GTA V or
prove that its voice recordings are audible on a particular game build.
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
    'private void PlayPedSpeech(Ped ped, string speechName)',
    'private void PlayMoaningSounds()',
    'private void TickPostSexVoice()',
    'private void TickCustomSound()',
    'private void PlayBjCustom(string path, bool force = false)',
    'private void PlaySlapSound(string path)',
    'private void PlayKissSound(string path)',
))
voices = 'private static readonly string[] HOOKER_VOICES = {' + source.split('private static readonly string[] HOOKER_VOICES = {', 1)[1].split('};', 1)[0] + '};'
finish_condition = source.split('if (masterTriggered && keyCooldown == 0 && !_liveVoiceMenu', 1)[1].split(')', 1)[0]
finish_gate = 'private bool TestFinishGate(bool masterTriggered) { return masterTriggered && keyCooldown == 0 && !_liveVoiceMenu' + finish_condition + '; }'
periodic = 'private void TickPeriodic() {' + source.split('// Animation speed controls request cadence, never the duration of a speech line.', 1)[1].split('// Custom BJ sounds', 1)[0] + '}\n'
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
    'WAV scheduling observes speech/pending': 'bool gtaSpeechActive = IsPartnerSpeechBusy(girl) || HasQueuedPartnerSpeech() || _pendingPartnerVoiceChange;',
}
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
    public static bool Modifier, ControllerY, MasterControl;
    public static List<string> Spoken = new List<string>();
    public static List<string> SpeechParameters = new List<string>();
    public static uint Key(string name) {
        uint value = 0;
        foreach (char c in name.ToLowerInvariant()) {
            value += c; value += value << 10; value ^= value >> 6;
        }
        value += value << 3; value ^= value >> 11; value += value << 15;
        return value;
    }
    public static void Reset() {
        Spoken.Clear(); SpeechParameters.Clear(); Duration=5000; Delay=VoiceSets=Stops=FalseFrom=FalseUntil=VoiceSetFailures=0; Modifier=ControllerY=false;
        Game.GameTime=1000; Game.KeyDown=Game.MasterDown=false; MasterControl=false;
    }
    public static void Call(Hash native, params object[] args) {
        if (native == Hash.SET_AMBIENT_VOICE_NAME) { if(VoiceSetFailures>0) VoiceSetFailures--; else ((Ped)args[0]).Voice = (string)args[1]; VoiceSets++; }
        else if (native == Hash.STOP_CURRENT_PLAYING_AMBIENT_SPEECH) { Stops++; ((Ped)args[0]).SpeakingUntil=0; }
        else if ((ulong)native == 0x3523634255FC3318UL || native == Hash.PLAY_PED_AMBIENT_SPEECH_NATIVE) {
            Ped ped=(Ped)args[0]; ped.VisibleFrom=Game.GameTime+Delay; ped.SpeakingUntil=Game.GameTime+Duration;
            Spoken.Add((string)args[1]); SpeechParameters.Add((string)args[(ulong)native==0x3523634255FC3318UL ? 3 : 2]);
        }
    }
    public static T Call<T>(Hash native, params object[] args) {
        object value;
        if (native == Hash.GET_HASH_KEY) {
            uint hash = Key((string)args[0]); value = typeof(T) == typeof(uint) ? (object)hash : (object)unchecked((int)hash);
        } else if ((ulong)native == 0x5E203DA2BA15D436UL) value = Key(((Ped)args[0]).Voice);
        else if ((ulong)native == 0x729072355FA39EC9UL) {
            Ped ped=(Ped)args[0]; value=Game.GameTime>=ped.VisibleFrom && Game.GameTime<ped.SpeakingUntil && !(Game.GameTime>=FalseFrom && Game.GameTime<FalseUntil);
        } else if (native == Hash.IS_DISABLED_CONTROL_PRESSED) value=(int)args[1]==1 ? Modifier : MasterControl;
        else if (native == Hash.IS_DISABLED_CONTROL_JUST_PRESSED) value=ControllerY;
        else throw new Exception("Unexpected native: " + native);
        return (T)value;
    }
}
namespace System.Media {
    class SoundPlayer {
        public static int Plays, Stops, Interruptions, EngineUntil, Duration=400;
        public System.IO.Stream Stream;
        public void Load() { }
        public void Stop() { Stops++; EngineUntil=0; }
        public void Play() { if(Game.GameTime<EngineUntil) Interruptions++; Plays++; EngineUntil=Game.GameTime+Duration; }
        public static void Reset() { Plays=Stops=Interruptions=EngineUntil=0;Duration=400; }
    }
}
class Harness {
    enum ScriptState { Idle, Approaching, Animating }
    enum MenuLevel { None, Main, PartnerVoices, Services }
    class ALifePedData { public string Voice; public int Reputation; }
    private static readonly Dictionary<int,string> voiceCache = new Dictionary<int,string>();
    private Dictionary<string,ALifePedData> _aLifePeds = new Dictionary<string,ALifePedData>();
    private Random rng = new Random(42);
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
    private System.Media.SoundPlayer _bjPlayer,_slapPlayer,_kissPlayer;
    private Dictionary<string,byte[]> _bjWavData=new Dictionary<string,byte[]>();
    private Dictionary<string,int> _soundDurations=new Dictionary<string,int>();
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
    static int count;
    static void Check(bool condition,string message) { count++; if(!condition) throw new Exception("FAIL "+message); }
    static Harness New(bool native=false) {
        Function.Reset(); System.Media.SoundPlayer.Reset(); voiceCache.Clear(); var h=new Harness();
        h.girl=new Ped { Handle=42, Model=new Model { Hash=unchecked((int)Function.Key(native?"s_f_y_hooker_01":"a_f_y_bevhills_01")) } };
        h.girl.Voice=HOOKER_VOICES[2]; h.LoadPartnerVoiceCatalogue(); return h;
    }
    public static void Main() {
        var h=New();
        Check(h._partnerVoices.Count==8,"eight confirmed voice entries only");
        Check(NormalizePartnerVoice("S_F_Y_HOOKER_03_BLACK_FULL_02")==null,"unconfirmed ninth bank excluded");
        Check(NormalizePartnerVoice("AMANDA")==null,"other banks rejected");
        Check(NormalizePartnerVoice("  "+HOOKER_VOICES[0].ToLowerInvariant()+"  ")==HOOKER_VOICES[0],"valid IDs normalized");
        h.SelectPartnerVoice(HOOKER_VOICES[0]);
        Check(h._pendingPartnerVoiceChange && h._appliedPartnerVoice=="","SET alone does not claim confirmed bank");
        h.TickPartnerAudio();
        Check(!h._pendingPartnerVoiceChange && h._appliedPartnerVoice==HOOKER_VOICES[0],"following tick confirms engine hash");
        h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        int initialSets=Function.VoiceSets;
        for(int t=1100;t<6000;t+=100) { Game.GameTime=t; h.TickPartnerAudio(); h.TickPeriodic(); h.AssignHookerVoice(h.girl); }
        Check(Function.SpeechParameters[0]=="SPEECH_PARAMS_ALLOW_REPEAT","native request uses non-forcing repeat parameters");
        Check(Function.Spoken.Count==1 && Function.Stops==0,"5000ms line survives speed3 cadence without stop/relaunch");
        Check(Function.VoiceSets==initialSets,"no voice-name reapply while line active");
        Check(h._queuedSpeechName==null,"ordinary loop requests not queued");
        Game.GameTime=6000;h.TickPartnerAudio();h.TickPeriodic();
        Check(Function.Spoken.Count==1 && h.IsPartnerSpeechBusy(h.girl),"first false speech sample begins quiet confirmation");
        Game.GameTime=6449;h.TickPartnerAudio();h.TickPeriodic();Check(Function.Spoken.Count==1,"450ms quiet guard prevents early relaunch");
        Game.GameTime=6450;h.TickPartnerAudio();h.TickPeriodic();
        Check(Function.Spoken.Count==1 && !h.IsPartnerSpeechBusy(h.girl),"quiet completion starts a separate cadence delay");
        Game.GameTime=13449;h.TickPartnerAudio();h.TickPeriodic();Check(Function.Spoken.Count==1,"speed3 does not shorten seven-second post-line gap");
        Game.GameTime=13450;h.TickPartnerAudio();h.TickPeriodic();Check(Function.Spoken.Count==2,"next periodic request starts after full independent gap");

        h=New();Function.Delay=400;h.PlayPedSpeech(h.girl,"GENERIC_HI");Game.GameTime=1350;h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        Check(h.IsPartnerSpeechBusy(h.girl) && Function.Spoken.Count==1,"600ms launch grace covers delayed native startup");
        h=New(true);h.PlayPedSpeech(h.girl,"GENERIC_HI");initialSets=Function.VoiceSets;
        Game.GameTime=1500;h.SelectPartnerVoice(HOOKER_VOICES[0]);h.SelectPartnerVoice(HOOKER_VOICES[7]);
        Check(h._pendingPartnerVoiceChange && Function.VoiceSets==initialSets,"active-line selections defer bank writes");
        Check(h.partnerVoice==HOOKER_VOICES[7] && h.settingsSaved==2,"last pending selection wins and persists");
        Game.GameTime=6000;h.TickPartnerAudio();Game.GameTime=6450;h.TickPartnerAudio();
        Check(h._pendingPartnerVoiceChange && h._voiceAwaitingReadback && h.girl.Voice==HOOKER_VOICES[7],"line-end bank write waits for readback");
        Game.GameTime=6451;h.TickPartnerAudio();
        Check(!h._pendingPartnerVoiceChange && h._appliedPartnerVoice==HOOKER_VOICES[7],"last selected bank confirmed after completion");
        Check(h._nativeVoiceBeforeOverride==HOOKER_VOICES[2],"original native bank captured");
        h.SelectPartnerVoice("");h.TickPartnerAudio();
        Check(h.girl.Voice==HOOKER_VOICES[2] && h._voiceOverridePedHandle==0,"automatic restores captured native bank");

        h=New();Function.VoiceSetFailures=1;h.SelectPartnerVoice(HOOKER_VOICES[7]);
        Check(h._pendingPartnerVoiceChange && h.girl.Voice!=HOOKER_VOICES[7],"ignored engine SET is not marked confirmed");
        h.PlayPedSpeech(h.girl,"SEX_GENERIC");Check(Function.Spoken.Count==0,"speech waits while requested bank is unconfirmed");
        Game.GameTime=1499;h.TickPartnerAudio();Check(Function.VoiceSets==1 && h._appliedPartnerVoice=="","failed readback waits for500ms retry");
        Game.GameTime=1500;h.TickPartnerAudio();Check(Function.VoiceSets==2 && h._pendingPartnerVoiceChange,"retry writes bank without false early confirmation");
        Game.GameTime=1501;h.TickPartnerAudio();Check(!h._pendingPartnerVoiceChange && h._appliedPartnerVoice==HOOKER_VOICES[7],"retry confirms actual engine hash");

        h=New();h.aLifeMode=true;h.GetOrCreateALifeData(h.girl).Voice=HOOKER_VOICES[4];
        h.SelectPartnerVoice(HOOKER_VOICES[0]);h.TickPartnerAudio();
        Check(h.GetOrCreateALifeData(h.girl).Voice==HOOKER_VOICES[4] && h.aLifeSaved==0,"override preserves A-Life voice");
        h.PlayPedSpeech(h.girl,"GENERIC_HI");h.SelectPartnerVoice("");
        Game.GameTime=6000;h.TickPartnerAudio();Game.GameTime=6450;h.TickPartnerAudio();Game.GameTime=6451;h.TickPartnerAudio();
        Check(h.girl.Voice==HOOKER_VOICES[4] && !h._pendingPartnerVoiceChange,"automatic restores A-Life bank after full quiet+readback");
        h=New();voiceCache[42]=HOOKER_VOICES[5];h.SelectPartnerVoice(HOOKER_VOICES[0]);h.TickPartnerAudio();h.SelectPartnerVoice("");h.TickPartnerAudio();
        Check(h.girl.Voice==HOOKER_VOICES[5],"automatic preserves sandbox cache");

        h=New();h.PlayPedSpeech(h.girl,"GENERIC_HI");
        h.PlayPedSpeech(h.girl,"HOOKER_OFFER_SERVICE");h.PlayPedSpeech(h.girl,"HOOKER_OFFER_AGAIN");h.PlayPedSpeech(h.girl,"SEX_FINISHED");h.PlayPedSpeech(h.girl,"GENERIC_YES");h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        Check(h._queuedSpeechName=="SEX_FINISHED" && Function.Spoken.Count==1,"single bounded pending line keeps finish priority");
        h._postSexPhase=1;h._postSexPendingMenu=MenuLevel.Services;
        Game.GameTime=6000;h.TickPartnerAudio();h.TickPostSexVoice();Check(h._postSexPhase==1,"finish state waits quiet and pending finish");
        Game.GameTime=6450;h.TickPartnerAudio();h.TickPostSexVoice();
        Check(Function.Spoken.Count==2 && Function.Spoken[1]=="SEX_FINISHED" && h._postSexPhase==1,"queued finish starts before post state advances");
        Game.GameTime=11450;h.TickPartnerAudio();h.TickPostSexVoice();Check(h._postSexPhase==1,"finish completion still waits stable quiet");
        Game.GameTime=11900;h.TickPartnerAudio();h.TickPostSexVoice();Check(h._postSexPhase==2,"post state advances after complete queued finish");
        Game.GameTime=12399;h.TickPartnerAudio();h.TickPostSexVoice();Check(Function.Spoken.Count==2,"post sequence preserves followup interval");
        Game.GameTime=12400;h.TickPartnerAudio();h.TickPostSexVoice();
        Check(h._postSexPhase==0 && Function.Spoken.Count==3 && Function.Spoken[2]=="HOOKER_OFFER_AGAIN" && h.menuLevel==MenuLevel.Services,"followup and deferred menu preserved");

        h=New();h._bjThroatPending=true;h.PlayPedSpeech(h.girl,"SEX_GENERIC");Check(Function.Spoken.Count==0 && !h.HasQueuedPartnerSpeech(),"throat pending drops stale periodic request");
        h.PlayPedSpeech(h.girl,"SEX_FINISHED");h.TickPartnerAudio();Check(h.HasQueuedPartnerSpeech() && Function.Spoken.Count==0,"important speech waits throat pending");
        h._bjThroatPending=false;h._throatLockAt=1;h.TickPartnerAudio();Check(Function.Spoken.Count==0,"throat timestamp lock blocks speech");
        h._throatLockAt=0;h._throatSpeedLocked=true;h.TickPartnerAudio();Check(Function.Spoken.Count==0,"throat speed lock blocks speech");
        h._throatSpeedLocked=false;h.TickPartnerAudio();Check(Function.Spoken.Count==1 && !h.HasQueuedPartnerSpeech(),"important speech resumes after unlock");

        h=New();h._bjWavData["clip"]=new byte[16];h._soundDurations["clip"]=400;
        h.PlayBjCustom("clip");Check(System.Media.SoundPlayer.Plays==1 && h._customSoundBusyUntil==1450,"400ms clip reserves shared channel plus50ms");
        Game.GameTime=1180;h.PlaySlapSound("clip");h.PlayKissSound("clip");h.PlayBjCustom("clip");
        Check(System.Media.SoundPlayer.Plays==1 && System.Media.SoundPlayer.Stops==0 && System.Media.SoundPlayer.Interruptions==0,"180ms cadence cannot restart/stop shared400ms clip");
        Game.GameTime=1449;h.PlaySlapSound("clip");Check(System.Media.SoundPlayer.Plays==1,"next player waits for full shared reservation");
        Game.GameTime=1450;h.PlaySlapSound("clip");Check(System.Media.SoundPlayer.Plays==2 && System.Media.SoundPlayer.Interruptions==0,"next channel play starts after full duration");
        Game.GameTime=1630;h.PlayKissSound("clip");Check(System.Media.SoundPlayer.Plays==2,"different player shares same channel guard");
        h.PlayBjCustom("clip",true);Check(System.Media.SoundPlayer.Stops==0 && System.Media.SoundPlayer.Plays==2 && h._queuedCustomSoundPath=="clip","important custom clip queues without replacing current playback");
        Game.GameTime=1899;h.TickCustomSound();Check(System.Media.SoundPlayer.Plays==2,"queued custom clip waits full current reservation");
        Game.GameTime=1900;h.TickCustomSound();h.PlayKissSound("clip");
        Check(System.Media.SoundPlayer.Plays==3 && System.Media.SoundPlayer.Stops==0 && System.Media.SoundPlayer.Interruptions==0 && h._queuedCustomSoundPath==null,"important queued custom clip wins idle channel without preemption");
        h.PlayBjCustom("clip",true);h.ResetPartnerAudio();Check(h._queuedCustomSoundPath==null,"reset cancels queued custom playback");
        h=New();h.partnerVoice=HOOKER_VOICES[7];h.TickPartnerAudio();Check(h._pendingPartnerVoiceChange && h._voiceAwaitingReadback,"cfg-restored selection schedules engine application");
        Game.GameTime=1001;h.TickPartnerAudio();Check(h._appliedPartnerVoice==HOOKER_VOICES[7] && !h._pendingPartnerVoiceChange,"cfg-restored selection confirms on next tick");
        h=New();h.PlayPedSpeech(h.girl,"GENERIC_HI");Game.GameTime=6000;h.TickPartnerAudio();
        Game.GameTime=6200;h.IsPartnerSpeechBusy(new Ped{Handle=99});Check(h._speechObservedPedHandle==42 && h._speechQuietStarted,"foreign ped query cannot reset primary quiet latch");

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
        h=New(); Function.Delay=400; h.PlayPedSpeech(h.girl,"GENERIC_HI");
        Game.GameTime=1350; h.PlayPedSpeech(h.girl,"SEX_GENERIC");
        Check(Function.Spoken.Count==1,"native startup delayed beyond300ms does not trigger second line");
        h=New(); h.PlayPedSpeech(h.girl,"GENERIC_HI"); initialSets=Function.VoiceSets;
        Function.FalseFrom=4000; Function.FalseUntil=4300;
        for(int t=3500;t<=4400;t+=50) {
            Game.GameTime=t;
            if(t==4100) h.SelectPartnerVoice(HOOKER_VOICES[7]);
            h.TickPeriodic(); h.TickPartnerAudio();
        }
        Check(Function.Spoken.Count==1 && Function.Stops==0,"transient300ms false speech flag cannot truncate or restart current line");
        Check(h._pendingPartnerVoiceChange && Function.VoiceSets==initialSets,"transient native false gap cannot change bank midline");
        Console.WriteLine("PASS: "+count+" deterministic audio/menu assertions. GTA natives mocked; no in-game audio validation.");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-audio-tests-') as directory:
    temp=Path(directory); cs=temp/'AudioTests.cs'; dll=temp/'AudioTests.dll'
    cs.write_text(mocks+voices+selector+methods+periodic+finish_gate+tests)
    rsp=temp/'refs.rsp'; rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/nowarn:0649,0414','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'AudioTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
print('PASS: '+str(len(wiring))+' input/reset/audio wiring checks.')
