#!/usr/bin/env python3
"""Exercise production master-key sampling, event prefix and state dispatch timelines.

Usage: python3 tests/verify_master_input.py [source.cs] [dotnet]
The actual keyboard sampler, idle master block and animation master block run
with the actual event prefix. Other scene services/native gameplay are mocked.
"""
from pathlib import Path
import json
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


sampler = source.split('// KEYBOARD MASTER INPUT', 1)[1].split('// END KEYBOARD MASTER INPUT', 1)[0]
on_tick = method('private void OnTick(object sender, EventArgs e)')
assert on_tick.count('SampleKeyboardMasterInput();') == 1, 'Sample once per tick'
assert on_tick.index('SampleKeyboardMasterInput();') < on_tick.index('if (HandleClubFrame()) return;')
idle = method('private void HandleIdleState(Ped player)')
idle = idle.split('// ── Master key: open/close menu ──', 1)[1].split('            if (menuLevel != MenuLevel.None) return;', 1)[0]
idle = 'private void ProcessIdleMaster() {' + idle + '}'
animating = method('private void HandleAnimatingState(Ped player)')
animating = animating.split('// The live voice overlay consumes its close button without finishing the animation.', 1)[1].split(
    '// Execute the actual finish once the Finish menu choice is resolved', 1)[0]
animating = 'private void ProcessAnimatingMaster() {' + animating + '}'
assert idle.count(': _keyboardMasterPressedThisTick;') == 1
assert animating.count(': _keyboardMasterPressedThisTick;') == 1
master = method('private void HandleAnimationMasterMenu()')
close_live = method('private void CloseLiveVoiceMenu()')
keyboard = method('private void OnKeyDown(object sender, KeyEventArgs e)')
assert 'else if (e.KeyCode == masterKey)' not in keyboard, 'No duplicate event-owned master action'
keyboard = keyboard.split('            int itemCount', 1)[0] + ' GeneralMenuEventReached = true; }'
poll_release = method('private void PollLiveVoiceMenuToggle()')
assert 'Game.IsKeyPressed(LIVE_VOICE_MENU_KEY)' in poll_release, 'F6 remains independently sampled'
poll_release = poll_release.split('            bool keyDown', 1)[0] + ' }'
poll_release = poll_release.replace('PollLiveVoiceMenuToggle()', 'PollMasterRelease()')
approach = method('private void HandleApproachingState(Ped player)')
held_abort = approach.split('                bool holdingAbort', 1)[1].split(';', 1)[0]
assert 'Game.IsKeyPressed(masterKey)' in held_abort, 'Approach hold-to-abort retains held input'
held_abort = 'private bool IsApproachAbortHeld() { bool holdingAbort' + held_abort + '; return holdingAbort; }'

dotnet = Path(sys.argv[2] if len(sys.argv) > 2 else
              shutil.which('dotnet') or '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name

mocks = r'''
using System;
enum Keys { J,Back }
class KeyEventArgs { public Keys KeyCode; }
enum ScriptState { Idle,Animating }
enum MenuLevel { None,Main,Finish,PartnerVoices,Club }
enum ClubDancePhase { Off }
enum Mode { Car,Street }
class Ped { }
class Player { public Ped Character=new Ped(); }
static class Game {
    public static bool MasterHeld;
    public static Player Player=new Player();
    public static bool IsKeyPressed(Keys key){return key==Keys.J && MasterHeld;}
}
enum Hash { IS_DISABLED_CONTROL_PRESSED,IS_DISABLED_CONTROL_JUST_PRESSED }
static class Function {
    public static bool Held,Pressed;
    public static T Call<T>(Hash hash,params object[] args){object value=hash==Hash.IS_DISABLED_CONTROL_PRESSED?Held:Pressed;return (T)value;}
}
class Harness {
    private readonly Ped player=Game.Player.Character;
    private ScriptState state=ScriptState.Idle;
    private Mode mode=Mode.Street;
    private MenuLevel menuLevel=MenuLevel.None;
    private ClubDancePhase _clubPhase=ClubDancePhase.Off;
    private bool _usingController,_liveVoiceMenu,_suppressFinishUntilMasterReleased,_finishExecutePending;
    private bool tokenKeyboardOpen,_speechGapKeyboardOpen,_speechGapInputFrame,_streetFinishGuardActive;
    private bool carPropActive,_streetSitPropActive,GeneralMenuEventReached;
    private int animPhase=2,keyCooldown,_menuControlCooldown,menuIndex,_streetSitPropPhase,_postSexPhase;
    private int _streetSitExitReturnIdx,CarExits,StreetExits,Captures;
    private MenuLevel _carPropPendingMenu,_carPropExitReturnMenu,_streetSitExitReturnMenu;
    private const int KEY_COOLDOWN_FRAMES=12;
    private readonly Keys masterKey=Keys.J,menuBackKey=Keys.Back;
    private int masterControlModifier=2,masterControl=1;
    private void ExitCarProposition(Ped ped){CarExits++;}
    private void ExitStreetSitProposition(Ped ped){StreetExits++;}
    private void CaptureStreetFinishPair(){Captures++;_streetFinishGuardActive=true;}
    private void ArmFinishSelection(){ }
    private void MaintainStreetFinishPair(Ped ped){ }
'''
tests = r'''
    private static int count;
    private static void Check(bool condition,string text){count++;if(!condition)throw new Exception("FAIL: "+text);}
    private bool previousHeld;
    private void Step(bool held,bool clubOwnsFrame=false){
        Game.MasterHeld=held;Function.Held=held;Function.Pressed=held&&!previousHeld;previousHeld=held;
        // Repeated OS events may arrive before or after a tick; they must never own core J.
        if(held)OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.J});
        SampleKeyboardMasterInput();
        if(keyCooldown>0)keyCooldown--;
        if(clubOwnsFrame)return;
        PollMasterRelease();
        if(state==ScriptState.Idle)ProcessIdleMaster();else ProcessAnimatingMaster();
        if(held)OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.J});
    }
    public static void Main(){
        foreach(bool animating in new[]{false,true}){
            var h=new Harness();h.state=animating?ScriptState.Animating:ScriptState.Idle;
            h.Step(true);MenuLevel opened=animating?MenuLevel.Finish:MenuLevel.Main;
            Check(h.menuLevel==opened,"one physical press opens expected menu");
            for(int frame=0;frame<120;frame++)h.Step(true);
            Check(h.menuLevel==opened&&!h._finishExecutePending,"held J never toggles after cooldown or OS repeats");
            Check(!h.GeneralMenuEventReached,"master events cannot invoke a second general menu handler");
            Check(!animating||h.Captures==1,"held animation press captures pair only once");
            h.Step(false);h.Step(true);
            Check(h.menuLevel==MenuLevel.None,"release then new press closes once");
            for(int frame=0;frame<120;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.None,"holding close press cannot reopen menu");
            h.Step(false);h.Step(true);
            Check(h.menuLevel==opened,"next physical press reopens once");
        }
        {
            var h=new Harness();h.Step(true);
            h.state=ScriptState.Animating;h.menuLevel=MenuLevel.None;
            for(int frame=0;frame<80;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.None&&h.Captures==0,"held idle press cannot become a new animation Finish press");
            h.Step(false);h.Step(true);
            Check(h.menuLevel==MenuLevel.Finish&&h.Captures==1,"released state-crossing press opens Finish normally");
            h.state=ScriptState.Idle;h.menuLevel=MenuLevel.None;
            for(int frame=0;frame<80;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.None,"held animation press cannot reopen idle Main after scene ends");
            h.Step(false);h.Step(true);
            Check(h.menuLevel==MenuLevel.Main,"fresh idle press remains available after scene");
        }
        {
            var h=new Harness();h.Step(true,true);
            for(int frame=0;frame<40;frame++)h.Step(true,true);
            for(int frame=0;frame<40;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.None,"club-owned frames still consume sampling history of held J");
            h.Step(false);h.Step(true);
            Check(h.menuLevel==MenuLevel.Main,"fresh press after club ownership works normally");
        }
        {
            var h=new Harness();h.keyCooldown=5;h.Step(true);
            for(int frame=0;frame<30;frame++)h.Step(true);
            Check(h.menuLevel==MenuLevel.None,"press during cooldown does not fire later merely because held");
            h.Step(false);h.Step(true);Check(h.menuLevel==MenuLevel.Main,"new press after cooldown works");
        }
        {
            var h=new Harness();h.mode=Mode.Car;h.carPropActive=true;h.menuLevel=MenuLevel.Main;
            h._carPropPendingMenu=h._carPropExitReturnMenu=h._streetSitExitReturnMenu=MenuLevel.Main;h._streetSitExitReturnIdx=7;
            h.Step(true);
            Check(h.CarExits==1&&h.menuLevel==MenuLevel.None,"single idle close preserves vehicle proposition exit");
            Check(h._carPropPendingMenu==MenuLevel.None&&h._carPropExitReturnMenu==MenuLevel.None&&h._streetSitExitReturnMenu==MenuLevel.None&&h._streetSitExitReturnIdx==0,"single owner preserves deferred-menu cleanup");
            for(int frame=0;frame<50;frame++)h.Step(true);Check(h.CarExits==1,"held master does not repeat vehicle exit");
            h=new Harness();h._streetSitPropActive=true;h._streetSitPropPhase=2;h.menuLevel=MenuLevel.Main;h.Step(true);
            Check(h.StreetExits==1&&h.menuLevel==MenuLevel.None,"single idle close preserves street proposition exit");
        }
        {
            var h=new Harness();h.state=ScriptState.Animating;h._liveVoiceMenu=true;h.menuLevel=MenuLevel.PartnerVoices;
            h.Step(true);for(int frame=0;frame<60;frame++)h.Step(true);
            Check(!h._liveVoiceMenu&&h.menuLevel==MenuLevel.None&&h.Captures==0,"closing voice overlay consumes held master without Finish opening");
            h.Step(false);h.Step(true);Check(h.menuLevel==MenuLevel.Finish,"fresh master after voice close still opens Finish");
        }
        {
            var h=new Harness();h.Step(true);
            for(int frame=0;frame<20;frame++)h.Step(true);
            Check(!h._keyboardMasterPressedThisTick&&h.IsApproachAbortHeld(),"hold-to-abort remains held even when toggle edge is exhausted");
            h.Step(false);Check(!h.IsApproachAbortHeld(),"abort hold releases normally");
        }
        Console.WriteLine("PASS: "+count+" production master-input timeline assertions; no GTA engine validation.");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-master-input-tests-') as directory:
    temp=Path(directory);cs=temp/'MasterInputTests.cs';dll=temp/'MasterInputTests.dll'
    cs.write_text(mocks+sampler+master+close_live+keyboard+poll_release+idle+animating+held_abort+tests)
    rsp=temp/'refs.rsp';rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'MasterInputTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
