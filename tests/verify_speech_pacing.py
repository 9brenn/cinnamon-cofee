#!/usr/bin/env python3
"""Exercise actual native-request/ACK pacing with an explicit engine boundary model.

The mock deliberately rejects normal ambient requests during an 800ms engine
cooldown but accepts FORCE_NORMAL when idle. This tests request policy under that
model; it does not prove GTA's undocumented flag implementation or audibility.
"""
from pathlib import Path
import json
import subprocess
import tempfile
base=Path(__file__).with_name('verify_partner_audio.py')
context={'__file__':str(base),'__name__':'pacing_harness_builder'}
# Reuse only source extraction and C# boundary definitions, not the older test main.
prefix=base.read_text().split('with tempfile.TemporaryDirectory(',1)[0]
exec(compile(prefix,str(base),'exec'),context)
mocks=context['mocks']
mocks=mocks.replace('public static int Duration = 5000,', 'public static int EngineCooldownMs=800,ReadyAt,Interruptions;\n    public static int Duration = 5000,')
mocks=mocks.replace('Spoken.Clear(); SpeechParameters.Clear();', 'EngineCooldownMs=800;ReadyAt=Interruptions=0;Spoken.Clear(); SpeechParameters.Clear();')
old='if(!RejectEveryLaunch) { ped.VisibleFrom=Game.GameTime+Delay; ped.SpeakingUntil=ped.VisibleFrom+Duration; StartTimes.Add(ped.VisibleFrom); }'
assert old in mocks
mocks=mocks.replace(old,'''string param=(string)args[(ulong)native==0x3523634255FC3318UL ? 3 : 2];
            if(!RejectEveryLaunch && (param=="SPEECH_PARAMS_FORCE_NORMAL" || unchecked(Game.GameTime-ReadyAt)>=0)) {
                if(unchecked(ped.SpeakingUntil-Game.GameTime)>0 && Spoken.Count>0)Interruptions++;
                ped.VisibleFrom=unchecked(Game.GameTime+Delay);ped.SpeakingUntil=unchecked(ped.VisibleFrom+Duration);
                ReadyAt=unchecked(ped.SpeakingUntil+EngineCooldownMs);StartTimes.Add(ped.VisibleFrom);
            }''')
mocks=mocks.replace('Game.GameTime<((Ped)args[0]).ScriptedUntil','((Ped)args[0]).ScriptedUntil!=0 && unchecked(((Ped)args[0]).ScriptedUntil-Game.GameTime)>0')
mocks=mocks.replace('Game.GameTime>=ped.VisibleFrom && Game.GameTime<ped.SpeakingUntil','unchecked(Game.GameTime-ped.VisibleFrom)>=0 && unchecked(ped.SpeakingUntil-Game.GameTime)>0')
tests=r'''
    static int checks;
    static void Check(bool condition,string label){checks++;if(!condition)throw new Exception("FAIL "+label);}
    static Harness New(){
        Function.Reset();voiceCache.Clear();Game.GameTime=1000;
        if(File.Exists("scripts\\CinnamonCoffeeAudio.log"))File.Delete("scripts\\CinnamonCoffeeAudio.log");
        var h=new Harness();h.girl=new Ped{Handle=42,Voice=HOOKER_VOICES[2],Model=new Model{Hash=unchecked((int)Function.Key("a_f_y_bevhills_01"))}};
        h.LoadPartnerVoiceCatalogue();h.SelectPartnerVoice(HOOKER_VOICES[0]);return h;
    }
    static void Tick(Harness h,int now){Game.GameTime=now;h.TickPartnerAudio();h.TickPeriodic();}
    public static void Main(){
        foreach(double seconds in new[]{0d,0.1d,0.25d,0.5d,0.75d,1d,3d}){
            var h=New();h.partnerSpeechGapSeconds=seconds;
            for(int now=1000;now<=18000 && Function.StartTimes.Count<2;now+=10)Tick(h,now);
            Check(Function.StartTimes.Count==2,"engine cooldown cannot silently discard requested fixed-gap loop "+seconds);
            int observed=Function.StartTimes[1]-Function.StartTimes[0]-Function.Duration;
            int expected=(int)Math.Round(seconds*1000d,MidpointRounding.AwayFromZero);
            Check(observed>=expected&&observed<=expected+10,"ACK-based inter-line gap follows setting within one10ms test frame "+seconds);
            Check(Function.RequestTimes.Count==2,"accepted loop is requested once, without failed cooldown retries "+seconds);
            Check(Function.Stops==0&&Function.Interruptions==0,"new request never stops or replaces active simulated playback "+seconds);
            Check(Function.SpeechParameters.TrueForAll(p=>p=="SPEECH_PARAMS_FORCE_NORMAL"),"only idle loop policy uses force-normal "+seconds);
        }
        var actor=New();actor.partnerSpeechGapSeconds=0.5d;Function.Delay=300;
        for(int now=1000;now<=8000;now+=10)Tick(actor,now);
        Check(Function.StartTimes.Count==2,"delayed engine starts still yield two accepted lines");
        Check(Function.RequestTimes[1]-(Function.StartTimes[0]+Function.Duration)==500,"configured deadline remains500ms after actual native end");
        Check(Function.StartTimes[1]-(Function.StartTimes[0]+Function.Duration)==800,"engine300ms start latency is distinct from configured500ms request gap");
        string log=File.ReadAllText("scripts\\CinnamonCoffeeAudio.log");
        Check(log.Contains("fixed-gap start deviation")&&log.Contains("requested=")&&log.Contains("acknowledged=")&&log.Contains("expected="),"late ACK produces useful timing diagnostics instead of claiming exact audibility");

        actor=New();actor.partnerSpeechGapSeconds=0.5d;Function.RejectEveryLaunch=true;
        for(int now=1000;now<=10000;now+=10)Tick(actor,now);
        Check(Function.StartTimes.Count==0&&!actor._speechObservedActive,"unavailable engine speech is never counted as accepted playback");
        Check(Function.RequestTimes.Count>1&&Function.RequestTimes.Count<=6,"failed starts retry with a bounded grace and backoff");
        Check(File.ReadAllLines("scripts\\CinnamonCoffeeAudio.log").Length==1,"repeated no-ACK failures emit bounded diagnostic output");
        Check(File.ReadAllText("scripts\\CinnamonCoffeeAudio.log").Contains("start not acknowledged"),"engine rejection is diagnosed separately from configured gap");

        actor=New();actor.partnerSpeechGapSeconds=0d;actor.PlayPedSpeech(actor.girl,"SEX_GENERIC");
        actor.girl.ScriptedUntil=6000;Function.FalseFrom=3000;Function.FalseUntil=3400;
        for(int now=1010;now<6000;now+=10)Tick(actor,now);
        Check(Function.RequestTimes.Count==1&&Function.Stops==0&&Function.Interruptions==0,"owned scripted speech keeps a line intact through400ms ambient flag dropout at gapzero");
        Tick(actor,6000);Tick(actor,6000);
        Check(Function.RequestTimes.Count==1,"repeated same-GameTime queries cannot falsely satisfy zero-gap end confirmation");
        Tick(actor,6010);Check(Function.RequestTimes.Count==2,"zero gap resumes on next distinct game frame after both owned speech flags clear");
        actor=New();Function.RejectEveryLaunch=true;actor.girl.ScriptedUntil=60000;
        for(int now=1000;now<=6000;now+=10)Tick(actor,now);
        Check(Function.RequestTimes.Count>1&&!actor._speechObservedActive,"unowned scripted speech cannot acknowledge or indefinitely block an unstarted ambient request");

        actor=New();actor.partnerSpeechGapSeconds=1d;actor._speechObservedPedHandle=42;actor._speechObservedActive=true;
        actor._speechQuietStarted=true;actor._speechQuietSince=6000;actor.girl.SpeakingUntil=6000;
        actor.SchedulePartnerLoopSpeech(0,0);Game.GameTime=6450;actor.TickPeriodic();
        Check(Function.RequestTimes.Count==0&&actor._nextPartnerLoopSpeechAt==7000,"producer observes completion before testing its newly scheduled deadline");
        actor=New();actor.partnerSpeechGapSeconds=0.5d;int origin=int.MaxValue-3000;
        for(int offset=0;offset<=8000&&Function.StartTimes.Count<2;offset+=10)Tick(actor,unchecked(origin+offset));
        Check(Function.StartTimes.Count==2&&unchecked(Function.StartTimes[1]-Function.StartTimes[0])-Function.Duration==500,"real request/ACK pacing survives signed GameTime wrap");

        actor=New();actor.PlayPedSpeech(actor.girl,"GENERIC_HI");
        Check(Function.SpeechParameters.Count==1&&Function.SpeechParameters[0]=="SPEECH_PARAMS_ALLOW_REPEAT","explicit preview and important speech retain existing repeat policy");
        Console.WriteLine("Speech pacing: "+checks+" actual-request/ACK checks passed under simulated cooldown and native flags; GTA not run.");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-real-pacing-tests-') as directory:
    temp=Path(directory);cs=temp/'PacingTests.cs';dll=temp/'PacingTests.dll'
    cs.write_text(mocks+context['voices']+context['selector']+context['methods']+context['periodic']+tests)
    rsp=temp/'refs.rsp';rsp.write_text('\n'.join('/r:'+str(p) for p in context['refs'].glob('*.dll')))
    subprocess.run([str(context['dotnet']),str(context['sdk']),'/nologo','/nowarn:0649,0414,0169','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'PacingTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':context['runtime']}}}))
    subprocess.run([str(context['dotnet']),str(dll)],cwd=temp,check=True)
