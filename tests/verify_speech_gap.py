#!/usr/bin/env python3
"""Test actual speech-gap parsing, persistence, keyboard, and timer code.

The complete SaveSettings method and exact gap branch of LoadSettings are used.
Ambient speech/keyboard natives are simulated; GTA V is not started.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'Mod/scripts/CinnamonCoffee.3.cs').read_text(encoding='utf-8-sig')
masked=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:[^"]|"")*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',lambda m:' '*len(m.group()),source)
def extract(signature):
    start=source.index(signature);brace=masked.index('{',start);depth=1;end=brace+1
    while depth:
        if masked[end]=='{':depth+=1
        elif masked[end]=='}':depth-=1
        end+=1
    return source[start:end]
gap=source.split('// SPEECH GAP SETTINGS',1)[1].split('// END SPEECH GAP SETTINGS',1)[0]
methods='\n'.join(extract(signature) for signature in ('private bool IsPartnerSpeechBusy(Ped ped)','private void RecordPartnerSpeechAcknowledged(int now)','private void LogPartnerSpeechTiming(string reason, int now)','private void SaveSettings()'))
load_branch=extract('else if (trimmed.StartsWith("partnerSpeechGapSeconds="))').removeprefix('else ')
load_helper='private void LoadGapFromText(string text) { foreach(string line in text.Split(\'\\n\')) { string trimmed=line.Trim(); '+load_branch+' } }'
periodic='private void TickPeriodic() {'+source.split('// Animation speed controls request cadence, never the duration of a speech line.',1)[1].split('// Custom BJ sounds',1)[0]+'}'
tick=extract('private void OnTick(object sender, EventArgs e)')
assert tick.index('if (_speechGapKeyboardOpen) PollSpeechGapKeyboard();')<tick.index('TickPartnerAudio();')<tick.index('HandleAnimatingState(player);')
assert '_speechGapInputFrame = _speechGapKeyboardOpen;' in tick
assert 'StoreSpeechGapSetting(lines, partnerSpeechGapSeconds);' in extract('private void SaveSettings()')
assert re.search(r'if \(menuIndex == 0\).*?',extract('private void HandlePartnerVoiceSelect()'))
assert 'OpenSpeechGapKeyboard();' in extract('private void HandlePartnerVoiceSelect()')
assert re.search(r'4\s*\+\s*_partnerVoices.Count',extract('private int GetCurrentMenuItemCount()'))
for signature in ('private void OnKeyDown(object sender, KeyEventArgs e)','private void HandleControllerMenuInput()','private void PollLiveVoiceMenuToggle()'):
    assert '_speechGapKeyboardOpen' in extract(signature), signature
assert '_speechGapKeyboardOpen' in extract('private bool HandleClubFrame()')
assert 'CANCEL_ONSCREEN_KEYBOARD' in extract('private void FullReset(bool keepGirlTask = false)')
mocks=r'''
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
class Ped {public int Handle=42,SpeakingUntil;public bool Exists(){return true;}}
static class Game {public static int GameTime=1000;}
enum Hash : ulong {DISPLAY_ONSCREEN_KEYBOARD=1,UPDATE_ONSCREEN_KEYBOARD,GET_ONSCREEN_KEYBOARD_RESULT}
static class Function {
    public static int KeyboardStatus,Displays;public static string KeyboardResult,Initial;
    public static void Call(Hash native,params object[] args){
        if(native!=Hash.DISPLAY_ONSCREEN_KEYBOARD)throw new Exception("unexpected native write");Displays++;Initial=(string)args[3];
    }
    public static T Call<T>(Hash native,params object[] args){object result;
        if(native==Hash.UPDATE_ONSCREEN_KEYBOARD)result=KeyboardStatus;
        else if(native==Hash.GET_ONSCREEN_KEYBOARD_RESULT)result=KeyboardResult;
        else if((ulong)native==0xCC9AA18DCC7084F4UL)result=false;
        else if((ulong)native==0x9072C8B49907BFADUL)result=Game.GameTime<((Ped)args[0]).SpeakingUntil;
        else throw new Exception("unexpected native read");
        return (T)result;
    }
}
class CountingRandom : Random {public int GapDraws;public CountingRandom():base(42){}public override int Next(int min,int max){if(min==2000&&max==5001)GapDraws++;return base.Next(min,max);}}
class Harness {
    private const string SETTINGS_FILE="scripts\\CinnamonCoffee.cfg";
    private const int SPEECH_LAUNCH_GRACE_MS=1200,SPEECH_END_QUIET_MS=450,KEY_COOLDOWN_FRAMES=20;
    private int _nextPartnerLoopSpeechAt,_speechObservedPedHandle,_speechLaunchAt,_speechLaunchPedHandle,_speechQuietSince,_speechStartFailures,_lastSpeechDiagnosticAt;
    private bool _speechObservedActive,_speechRequestPending,_speechQuietStarted;
    private string _lastSpeechName="GENERIC_HI";private const string SCRIPT_VERSION="test";private int _speechAcknowledgedAt,_speechExpectedStartAt;private bool _speechCheckFixedGap;
    private Ped girl=new Ped();private CountingRandom rng=new CountingRandom();
    private bool tokenKeyboardOpen,_suppressFinishUntilMasterReleased;private int keyCooldown,_menuControlCooldown;
    private string hud;
    private void ShowHudStatus(string text,int duration){hud=text;}
    private string currentAction="standing";private int animPhase=2;private float animSpeed=3f;private bool _pendingPartnerVoiceChange;
    private int lastVoiceTime;private List<int> Launches=new List<int>();
    private bool HasQueuedPartnerSpeech(){return false;}
    private bool PlayMoaningSounds(){Launches.Add(Game.GameTime);_speechObservedActive=true;girl.SpeakingUntil=unchecked(Game.GameTime+5000);return true;}
    private string deviceToken="",partnerVoice="";
    private bool dildoEnabled,driveableCar,showTutorialMessages,slapSoundsEnabled,bjSoundsEnabled,femaleServiceVoice,femaleMoanVoice,femaleEndVoice,sandboxMode,aLifeMode,interiorLightEnabled,carEngineEnabled,streetSitAnimEnabled,sinkraReplaceLaying,sinkraReplaceRevLaying,sinkraReplaceFacesitting;
    private int strokeMin,strokeMax,readyAndFinishDelay;
'''
tests=r'''
    static int checks;
    static void Check(bool value,string label){checks++;if(!value)throw new Exception("FAIL "+label);}
    static Harness New(){Game.GameTime=1000;Function.KeyboardStatus=Function.Displays=0;Function.KeyboardResult=Function.Initial=null;return new Harness();}
    static void Run(Harness h,int first,int last){for(int t=first;t<=last;t+=50){Game.GameTime=t;h.IsPartnerSpeechBusy(h.girl);h.TickPeriodic();}}
    public static void Main(){
        double seconds;
        foreach(string text in new[]{"0","1","3","0.25"," 0,5 ","-1","random","RANDOM","2147483","1e-3","-0"})
            Check(TryParseSpeechGap(text,out seconds),"accept valid gap "+text);
        foreach(string text in new[]{""," ","NaN","Infinity","+Infinity","-Infinity","1e309","2147483.001","-0.1","-2","one","0.2.3"})
            Check(!TryParseSpeechGap(text,out seconds),"reject invalid gap "+text);
        Check(!TryParseSpeechGap(null,out seconds),"reject null");
        Check(TryParseSpeechGap("0,5",out seconds)&&seconds==0.5d,"Polish comma means decimal seconds");
        var h=New();Check(h.partnerSpeechGapSeconds==-1d,"omitted setting retains random default");
        h.LoadGapFromText("// existing config\npartnerSpeechGapSeconds=3\notherKey=keep");Check(h.partnerSpeechGapSeconds==3d,"actual LoadSettings branch loads fixed gap");
        foreach(string invalid in new[]{"NaN","Infinity","-2","2147484"}){h.LoadGapFromText("partnerSpeechGapSeconds="+invalid);Check(h.partnerSpeechGapSeconds==3d,"invalid config leaves prior valid gap unchanged");}
        h.LoadGapFromText("partnerSpeechGapSeconds=0,25");Check(h.partnerSpeechGapSeconds==0.25d,"load branch supports decimal comma");
        h.LoadGapFromText("partnerSpeechGapSeconds=-1");Check(h.partnerSpeechGapSeconds==-1d,"load branch restores random sentinel");
        CultureInfo.CurrentCulture=new CultureInfo("fr-FR");
        File.WriteAllText(SETTINGS_FILE,"// keep comment\ncustomUserSetting=untouched\npartnerSpeechGapSeconds=3\n");
        h.partnerSpeechGapSeconds=0.25d;h.SaveSettings();string saved=File.ReadAllText(SETTINGS_FILE);
        Check(saved.Contains("partnerSpeechGapSeconds=0.25"),"actual SaveSettings uses invariant decimal serialization");
        Check(saved.Contains("// keep comment")&&saved.Contains("customUserSetting=untouched"),"save preserves user comments and unknown settings");
        h.SaveSettings();Check(File.ReadAllLines(SETTINGS_FILE).Count(line=>line.StartsWith("partnerSpeechGapSeconds="))==1,"repeated saves do not append duplicate gap setting");
        foreach(double expected in new[]{-1d,0d,1d,3d,0.25d,2147483d}){
            h.partnerSpeechGapSeconds=expected;h.SaveSettings();var restored=New();restored.LoadGapFromText(File.ReadAllText(SETTINGS_FILE));
            Check(restored.partnerSpeechGapSeconds==expected,"save/load roundtrip "+expected.ToString(CultureInfo.InvariantCulture));
        }
        var lines=new List<string>{"// no gap yet","unrelated=yes"};StoreSpeechGapSetting(lines,0d);Check(lines.Count==3&&lines[2]=="partnerSpeechGapSeconds=0","missing setting is appended once");
        h=New();h.partnerSpeechGapSeconds=0.0005d;Check(h.GetPartnerSpeechGapMilliseconds()==1,"half millisecond rounds away from zero");
        h.partnerSpeechGapSeconds=2147483d;Check(h.GetPartnerSpeechGapMilliseconds()==2147483000,"maximum allowed seconds fits millisecond integer");
        foreach(var setting in new[]{new[]{0d,6050d},new[]{0.1d,6100d},new[]{0.25d,6250d},new[]{0.5d,6500d},new[]{0.75d,6750d},new[]{1d,7000d},new[]{3d,9000d}}){
            h=New();h.partnerSpeechGapSeconds=setting[0];h._speechObservedPedHandle=42;h._speechObservedActive=true;h.girl.SpeakingUntil=6000;
            Run(h,1000,5950);Check(h.Launches.Count==0,"setting cannot cut full active line "+setting[0]);
            Run(h,6000,(int)setting[1]-50);Check(h.Launches.Count==0,"no request before configured delay and quiet guard "+setting[0]);
            Run(h,(int)setting[1],(int)setting[1]);Check(h.Launches.Count==1&&h.Launches[0]==(int)setting[1],"next request obeys configured gap exactly "+setting[0]);
            Check(h.rng.GapDraws==0,"fixed gap never draws random cadence");
        }
        h=New();h._speechObservedPedHandle=42;h._speechObservedActive=true;h.girl.SpeakingUntil=6000;Run(h,1000,10000);
        Check(h.rng.GapDraws==1,"default gap is drawn once per actual completed line");
        Check(h._nextPartnerLoopSpeechAt>=8000&&h._nextPartnerLoopSpeechAt<=11000,"default random deadline stays end plus2–5seconds");
        h=New();h._speechObservedPedHandle=42;h._speechObservedActive=true;h.girl.SpeakingUntil=6000;Game.GameTime=2000;h.ApplySpeechGap(0d);Run(h,2000,5950);Check(h.Launches.Count==0,"editing gap to zero midline never interrupts it");
        h=New();h.partnerSpeechGapSeconds=3d;h._speechObservedPedHandle=42;h._speechObservedActive=true;h.girl.SpeakingUntil=6000;Run(h,6000,6450);Game.GameTime=6500;h.ApplySpeechGap(0d);h.TickPeriodic();Check(h.Launches.Count==1,"editing an idle gap to zero reschedules existing wait immediately");
        h=New();Check(h.IsPartnerLoopSpeechDue(),"unset deadline is initially due");
        h.SchedulePartnerLoopSpeech(int.MaxValue-100,1000);Game.GameTime=int.MaxValue-50;Check(!h.IsPartnerLoopSpeechDue(),"deadline crossing signed timer wrap does not fire early");
        Game.GameTime=unchecked(int.MaxValue-100+999);Check(!h.IsPartnerLoopSpeechDue(),"wrapped deadline remains pending one millisecond before due");
        Game.GameTime=unchecked(int.MaxValue-100+1000);Check(h.IsPartnerLoopSpeechDue(),"wrapped deadline fires exactly at due time");
        h=New();h.partnerSpeechGapSeconds=2147483d;h.SchedulePartnerLoopSpeech(6000,h.GetPartnerSpeechGapMilliseconds());Game.GameTime=6450;Check(!h.IsPartnerLoopSpeechDue(),"maximum setting cannot overflow into immediate request");
        h=New();h.partnerSpeechGapSeconds=3d;h.OpenSpeechGapKeyboard();
        Check(h._speechGapKeyboardOpen&&Function.Displays==1&&Function.Initial=="3","keyboard opens nonblocking with current value");
        h.OpenSpeechGapKeyboard();Check(Function.Displays==1,"repeated open does not duplicate native keyboard");
        Function.KeyboardStatus=0;h.PollSpeechGapKeyboard();Check(h._speechGapKeyboardOpen&&h.partnerSpeechGapSeconds==3d,"still-open keyboard leaves settings unchanged");
        Function.KeyboardStatus=1;Function.KeyboardResult="0,25";h.PollSpeechGapKeyboard();Check(!h._speechGapKeyboardOpen&&h.partnerSpeechGapSeconds==0.25d,"confirmed keyboard result parses and applies comma decimal");
        Check(h._speechGapInputFrame&&h._suppressFinishUntilMasterReleased&&h.keyCooldown==KEY_COOLDOWN_FRAMES,"confirmation frame cannot leak input into finish control");
        string before=File.ReadAllText(SETTINGS_FILE);h.OpenSpeechGapKeyboard();Function.KeyboardStatus=2;h.PollSpeechGapKeyboard();
        Check(h.partnerSpeechGapSeconds==0.25d&&File.ReadAllText(SETTINGS_FILE)==before,"cancelled keyboard leaves persisted gap unchanged");
        h.OpenSpeechGapKeyboard();Function.KeyboardStatus=1;Function.KeyboardResult="NaN";h.PollSpeechGapKeyboard();Check(h.partnerSpeechGapSeconds==0.25d&&File.ReadAllText(SETTINGS_FILE)==before,"invalid keyboard input is rejected without saving");
        h=New();h.tokenKeyboardOpen=true;h.OpenSpeechGapKeyboard();Check(!h._speechGapKeyboardOpen&&Function.Displays==0,"existing token keyboard blocks a second keyboard");
        Console.WriteLine("Speech gap: "+checks+" parsing/persistence/timeline/keyboard checks passed; GTA boundary simulated.");
    }
}
'''
dotnet=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk=sorted((dotnet.parent/'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs=sorted((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime=sorted((dotnet.parent/'shared/Microsoft.NETCore.App').iterdir())[-1].name
with tempfile.TemporaryDirectory(prefix='cinnamon-speech-gap-tests-') as directory:
    temp=Path(directory);cs=temp/'GapTests.cs';dll=temp/'GapTests.dll'
    cs.write_text(mocks+gap+methods+load_helper+periodic+tests)
    rsp=temp/'refs.rsp';rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/nowarn:0649,0414,0169','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'GapTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
print('Keyboard polling, reset cancellation, menu, and continuing-animation wiring checks passed.')
