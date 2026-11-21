#!/usr/bin/env python3
"""Exercise real street Finish protection/input/pending-outro source slices.

Usage: python3 tests/verify_street_finish_guard.py [source.cs] [dotnet]
Native clip loss is injected into mocks. Audio and other animation phases are
omitted; these tests do not establish what interrupted a live GTA V task.
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


def braced(text, start):
    opening = text.index('{', start)
    depth = 0
    for position in range(opening, len(text)):
        if text[position] == '{':
            depth += 1
        elif text[position] == '}':
            depth -= 1
            if depth == 0:
                return text[start:position + 1]
    raise AssertionError('Unclosed block at ' + str(start))


def method(signature):
    return braced(source, source.index(signature))


region = source.split('// STREET FINISH PROTECTION', 1)[1].split('// END STREET FINISH PROTECTION', 1)[0]
master_input = source.split('// KEYBOARD MASTER INPUT', 1)[1].split('// END KEYBOARD MASTER INPUT', 1)[0]
version_declaration = re.search(r'private const string SCRIPT_VERSION = [^;]+;', source).group(0)
master = method('private void HandleAnimationMasterMenu()')
simple = method('private bool HasSimpleFinishMenu()')
close_live = method('private void CloseLiveVoiceMenu()')
animating = method('private void HandleAnimatingState(Ped player)')
assert animating.index('ProtectStreetAnimationControls();') < animating.index('bool masterTriggered')
assert animating.index('MaintainStreetFinishPair(player);') < animating.index('if (_finishExecutePending')
assert master.index('CaptureStreetFinishPair();') < master.index('menuLevel = MenuLevel.Finish;')
assert 'KeyUp   += OnKeyUp;' in source, 'Keyboard release handler must be registered'
on_tick = method('private void OnTick(object sender, EventArgs e)')
assert on_tick.index('UpdateFinishSelectionLatch();') < on_tick.index('if (_usingController) HandleControllerMenuInput();')

# Production order: valid partner / controls, J, maintenance, pending wall outro.
scene = animating.split('            // Disable phone during animations', 1)[0]
scene = scene.replace('HandleAnimatingState(Ped player)', 'SceneTick(Ped player)')
scene += animating.split('// The live voice overlay consumes its close button without finishing the animation.', 1)[1].split(
    '// Execute the actual finish once the Finish menu choice is resolved', 1)[0]
pending = animating.split('// Execute the actual finish once the Finish menu choice is resolved', 1)[1]
pending_guard = pending.split('{', 1)[0]
wall_signature = 'else if (mode == Mode.Street && streetActionIdx == 5 && animPhase == 2)'
wall = braced(pending, pending.index(wall_signature)).replace('else if', 'if', 1)
scene += pending_guard + '{ _finishExecutePending = false;' + wall + '} }'

keyboard_full = method('private void OnKeyDown(object sender, KeyEventArgs e)')
keyboard = keyboard_full.split('            int itemCount', 1)[0]
select_key = braced(keyboard_full, keyboard_full.index('else if (e.KeyCode == menuSelectKey)')).replace('else if', 'if', 1)
keyboard += select_key + ' }'
controller_full = method('private void HandleControllerMenuInput()')
controller = controller_full.split('            int itemCount', 1)[0]
select_control = braced(controller_full, controller_full.index(
    'else if (Function.Call<bool>(Hash.IS_DISABLED_CONTROL_JUST_PRESSED, 0, menuSelectControl))')).replace('else if', 'if', 1)
controller += select_control + ' }'
select_menu = method('private void HandleMenuSelect()')
select_menu = select_menu.split('else if (menuLevel == MenuLevel.Finish)', 1)[1].split('// ── A-Life: full Ask', 1)[0].strip()
select_menu = 'private void HandleMenuSelect() ' + select_menu + ' }'

dotnet = Path(sys.argv[2] if len(sys.argv) > 2 else
              shutil.which('dotnet') or '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk = sorted((dotnet.parent / 'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs = sorted((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime = sorted((dotnet.parent / 'shared/Microsoft.NETCore.App').iterdir())[-1].name

mocks = r'''
using System;
using System.Collections.Generic;
using System.IO;
enum Keys { J,Back,NumPad5 }
class KeyEventArgs { public Keys KeyCode; }
enum ScriptState { Idle,Animating }
enum MenuLevel { None,Finish,PartnerVoices,Club }
enum ClubDancePhase { Off }
enum Mode { Car,Street }
struct Vector3 {
    public float X,Y,Z;
    public Vector3(float x,float y,float z){X=x;Y=y;Z=z;}
    public float DistanceTo(Vector3 other){return (float)Math.Sqrt((X-other.X)*(X-other.X)+(Y-other.Y)*(Y-other.Y)+(Z-other.Z)*(Z-other.Z));}
}
class Ped {
    public int Handle;public bool Valid=true,IsAlive=true,InVehicle,Playing=true;
    public Vector3 Position,Rotation,LastPosition,LastRotation;
    public string Dict,Clip;public float Phase=0.42f,Speed=1f;
    public float Heading {get{return Rotation.Z;}set{Rotation.Z=value;}}
    public int Recoveries,Outros,LastFlags;public string LastRecoveryApi;
    public bool Exists(){return Valid;}
    public bool IsInVehicle(){return InVehicle;}
    public Vector3 GetOffsetPosition(Vector3 o){return new Vector3(Position.X+o.X,Position.Y+o.Y,Position.Z+o.Z);}
}
class Player {public Ped Character;}
static class Game {
    public static Player Player=new Player();public static int GameTime=1000;public static bool MasterHeld,SelectHeld;
    public static bool IsKeyPressed(Keys key){if(key==Keys.J){Function.Events.Add("Input:J");return MasterHeld;}return key==Keys.NumPad5&&SelectHeld;}
}
enum Hash : ulong {
    IS_DISABLED_CONTROL_PRESSED,IS_DISABLED_CONTROL_JUST_PRESSED,DISABLE_ALL_CONTROL_ACTIONS,
    ENABLE_CONTROL_ACTION,GET_ENTITY_ANIM_CURRENT_TIME,IS_ENTITY_PLAYING_ANIM,HAS_ANIM_DICT_LOADED,
    TASK_PLAY_ANIM_ADVANCED,SET_ENTITY_ANIM_SPEED,STOP_ANIM_TASK,TASK_PLAY_ANIM,SET_ENTITY_COORDS_NO_OFFSET,SET_ENTITY_ANIM_CURRENT_TIME
}
static class Function {
    public static readonly List<string> Events=new List<string>();public static readonly HashSet<int> Enabled=new HashSet<int>();
    public static bool MasterHeld,MasterPressed,SelectHeld,SelectPressed,BackPressed,Loaded=true,DeferTasks;
    public static int Stops,AllDisabled;
    public static void Reset(){Events.Clear();Enabled.Clear();Stops=0;AllDisabled=0;Loaded=true;DeferTasks=false;MasterHeld=false;MasterPressed=false;SelectHeld=false;SelectPressed=false;BackPressed=false;}
    public static T Call<T>(Hash hash,params object[] args){
        object result;
        if(hash==Hash.IS_DISABLED_CONTROL_PRESSED){int c=(int)args[1];result=c==4?SelectHeld:MasterHeld;}
        else if(hash==Hash.IS_DISABLED_CONTROL_JUST_PRESSED){int c=(int)args[1];result=c==3?MasterPressed:c==4?SelectPressed:BackPressed;}
        else if(hash==Hash.GET_ENTITY_ANIM_CURRENT_TIME){Ped p=(Ped)args[0];result=p.Playing?p.Phase:0f;}
        else if(hash==Hash.IS_ENTITY_PLAYING_ANIM){Ped p=(Ped)args[0];result=p.Playing&&p.Dict==(string)args[1]&&p.Clip==(string)args[2];}
        else if(hash==Hash.HAS_ANIM_DICT_LOADED)result=Loaded;
        else throw new Exception("Unexpected query: "+hash);
        return (T)result;
    }
    public static void Call(Hash hash,params object[] args){
        Events.Add(hash.ToString());
        if(hash==Hash.DISABLE_ALL_CONTROL_ACTIONS){AllDisabled++;Enabled.Clear();}
        else if(hash==Hash.ENABLE_CONTROL_ACTION)Enabled.Add((int)args[1]);
        else if(hash==Hash.TASK_PLAY_ANIM_ADVANCED){
            Ped p=(Ped)args[0];p.Dict=(string)args[1];p.Clip=(string)args[2];
            p.LastPosition=new Vector3((float)args[3],(float)args[4],(float)args[5]);p.LastRotation=new Vector3((float)args[6],(float)args[7],(float)args[8]);
            p.Position=p.LastPosition;p.Rotation=p.LastRotation;p.LastFlags=(int)args[12];p.Phase=(float)args[13];p.Playing=!DeferTasks;p.Recoveries++;p.LastRecoveryApi="ADVANCED";
        }else if(hash==Hash.SET_ENTITY_ANIM_SPEED){Ped p=(Ped)args[0];if(p.Playing)p.Speed=(float)args[3];}
        else if(hash==Hash.SET_ENTITY_ANIM_CURRENT_TIME){Ped p=(Ped)args[0];if(p.Playing)p.Phase=(float)args[3];}
        else if(hash==Hash.STOP_ANIM_TASK){((Ped)args[0]).Playing=false;Stops++;}
        else if(hash==Hash.TASK_PLAY_ANIM){
            Ped p=(Ped)args[0];p.Dict=(string)args[1];p.Clip=(string)args[2];p.Playing=!DeferTasks;
            if(p.Clip=="female_loop"||p.Clip=="male_loop"){p.Recoveries++;p.LastFlags=(int)args[6];p.Phase=0f;p.Speed=(float)args[7];p.LastRecoveryApi="SIMPLE";p.LastPosition=p.Position;p.LastRotation=p.Rotation;}
            else p.Outros++;
        }else if(hash==Hash.SET_ENTITY_COORDS_NO_OFFSET)((Ped)args[0]).Position=new Vector3((float)args[1],(float)args[2],(float)args[3]);
        else throw new Exception("Unexpected mutation: "+hash);
    }
}
class Telemetry {public int Stops;public void SendStop(){Stops++;}}
class Harness {
    private readonly Ped player=new Ped{Handle=1,Dict="male_dict",Clip="male_loop",Position=new Vector3(10,20,30),Rotation=new Vector3(12,0,90)};
    private readonly Ped girl=new Ped{Handle=2,Dict="female_dict",Clip="female_loop",Position=new Vector3(10.5f,20,30),Rotation=new Vector3(0,0,270)};
    private readonly Telemetry _telemetry=new Telemetry();private ScriptState state=ScriptState.Animating;private Mode mode=Mode.Street;
    private MenuLevel menuLevel=MenuLevel.None;private ClubDancePhase _clubPhase=ClubDancePhase.Off;
    private int animPhase=2,streetActionIdx=5,menuIndex,keyCooldown,_menuControlCooldown;private const int KEY_COOLDOWN_FRAMES=12;
    private bool _usingController,_liveVoiceMenu,_suppressFinishUntilMasterReleased,_finishExecutePending;
    private bool tokenKeyboardOpen,_speechGapKeyboardOpen,_speechGapInputFrame;
    private string currentAction="sex",currentMaleDict="male_dict",currentMaleAnim="male_loop",currentFemaleDict="female_dict",currentFemaleAnim="female_loop";
    private bool _kissingReverse,_standingBjReverse,_rdoggyReverse,_finishInside,_finishForced,_finishAsked,_finishInsideFreePass,aLifeMode,_rumblePulseActive,_finishBurstFired;
    private int _finishExecuteAt,_aLifeFinishInsidePrice,_lastRumbleTime,animWaitTime;private float animSpeed=1.25f,_femaleAnimSpeedScale=1f,MockPitch=33f;
    private Keys masterKey=Keys.J,menuSelectKey=Keys.NumPad5,menuBackKey=Keys.Back;private int masterControlModifier=2,masterControl=3,menuSelectControl=4,menuBackControl=6;
    private void EndAnimation(){throw new Exception("Unexpected EndAnimation before explicit choice");}
    private void SetVibration(ushort left,ushort right){}
    private bool RequestAnimDict(string dict){return true;}
    private void ShowHudStatus(string text,int duration){}
    private void GetStreetAnimData(int index,out string md,out string ma,out string fd,out string fa,out Vector3 offset,out float heading,out bool sitting,out float zOffset,out float rotX){md=currentMaleDict;ma=currentMaleAnim;fd=currentFemaleDict;fa=currentFemaleAnim;offset=new Vector3(0.5f,0,0);heading=180;sitting=false;zOffset=0;rotX=MockPitch;}
'''

tests = r'''
    private static int count;
    private static void Check(bool value,string text){count++;if(!value)throw new Exception("FAIL: "+text);}
    private static bool Near(float a,float b){return Math.Abs(a-b)<0.0001f;}
    private static Harness New(int index=5){Function.Reset();Game.MasterHeld=false;Game.SelectHeld=false;Game.GameTime=1000;var h=new Harness();h.streetActionIdx=index;h.currentAction=index==0?"kissing":"sex";Game.Player.Character=h.player;return h;}
    private void Step(bool masterHeld=false){Game.GameTime+=16;Game.Player.Character=player;Game.MasterHeld=masterHeld;Function.MasterPressed=masterHeld&&!Function.MasterHeld;Function.MasterHeld=masterHeld;SampleKeyboardMasterInput();UpdateFinishSelectionLatch();SceneTick(player);}
    private void Open(bool selectHeld=false){Game.SelectHeld=selectHeld;Function.SelectHeld=selectHeld;Step(true);Game.MasterHeld=false;Function.MasterHeld=false;}
    public static void Main(){
        foreach(int index in new[]{0,1,2,3,4,5,6,7,8,9,10,11}){
            var h=New(index);h.Open();
            Check(h.menuLevel==MenuLevel.Finish&&h.animPhase==2&&!h._finishExecutePending,"production scene opens Finish without finishing action "+index);
            Check(Function.AllDisabled==1&&Function.Enabled.SetEquals(new[]{0,1,2,26,199,200}),"street blocks gameplay but preserves camera/pause "+index);
            Check(Function.AllDisabled>0&&h._keyboardMasterPressedThisTick,"production scene shields gameplay before dispatching sampled J "+index);
            Check(h.player.Recoveries==0&&h.girl.Recoveries==0&&Function.Stops==0,"opening never replays/stops intact actors "+index);
            h.Step();h.Step();Check(h.player.Recoveries==0&&h.girl.Recoveries==0,"intact pair retains current tasks "+index);
            h.player.Phase=0.2f;h.girl.Phase=0.4f;h.Step();Vector3 anchor=h.player.Position;
            h.player.Position=new Vector3(anchor.X+0.1f,anchor.Y,anchor.Z);h.player.Playing=false;h.girl.Phase=0.61f;h.Step();
            Check(h.player.Playing&&h.girl.Playing&&h.player.Recoveries==1&&h.girl.Recoveries==0,"only missing player recovers "+index);
            Check(Near(h.player.Phase,0.2f)&&Near(h.girl.Phase,0.61f)&&h.player.LastPosition.DistanceTo(anchor)<0.001f&&Near(h.player.LastRotation.X,h.MockPitch)&&Near(h.player.LastRotation.Z,90f)&&h.player.LastRecoveryApi=="ADVANCED","player restores data-driven pitch and own phase "+index);
            Check(h.player.LastFlags==(index==0?10:9)&&Near(h.player.Speed,h.animSpeed),"correct loop flags/speed "+index);
            h.Step();Check(h.player.Recoveries==1&&h.girl.Recoveries==0&&Function.Stops==0,"successful recovery avoids task restart loop "+index);
            h=New(index);h._femaleAnimSpeedScale=2f;h.player.Phase=0.2f;h.girl.Phase=0.4f;h.Open();h.girl.Playing=false;h.player.Phase=0.73f;h.Step();
            Check(h.girl.Playing&&h.girl.Recoveries==1&&h.player.Recoveries==0&&Near(h.girl.Phase,0.4f)&&Near(h.player.Phase,0.73f)&&h.girl.LastRecoveryApi=="SIMPLE","partner restores original simple task and independent phase "+index);
            Check(Near(h.girl.Speed,h.animSpeed*2f),"partner animation speed scale preserved "+index);
            h=New(index);h.player.Phase=0.2f;h.girl.Phase=0.4f;h.Open();h.player.Playing=false;h.girl.Playing=false;h.Step();
            Check(h.player.Recoveries==1&&h.girl.Recoveries==1&&Near(h.player.Phase,0.2f)&&Near(h.girl.Phase,0.4f)&&Function.Stops==0,"both lost clips retain independent playheads "+index);
        }
        foreach(int index in new[]{0,2,11}){var h=New(index);h.Open();h._kissingReverse=index==0;h._standingBjReverse=index==2;h._rdoggyReverse=index==11;h.player.Playing=false;h.girl.Playing=false;h.Step();Check(Near(h.player.Speed,-h.animSpeed)&&Near(h.girl.Speed,-h.animSpeed),"ping-pong direction preserved "+index);}
        foreach(bool female in new[]{false,true}){
            var h=New();h.player.Phase=0.2f;h.girl.Phase=0.6f;h.Step();if(female)h.girl.Playing=false;else h.player.Playing=false;h.Open();
            Check(h.player.Playing&&h.girl.Playing&&Near(h.player.Phase,0.2f)&&Near(h.girl.Phase,0.6f),"J-frame loss retains pre-menu healthy phases");
            Check(h.player.Recoveries==(female?0:1)&&h.girl.Recoveries==(female?1:0),"J-frame recovery leaves uninterrupted actor alone");
        }
        for(int scenario=0;scenario<12;scenario++){
            var h=New();h.Open();h.player.Playing=false;
            if(scenario==0)h.player.IsAlive=false;if(scenario==1)h.girl.IsAlive=false;if(scenario==2)h.player.InVehicle=true;if(scenario==3)h.girl.InVehicle=true;
            if(scenario==4)h.player.Handle=99;if(scenario==5)h.girl.Handle=99;if(scenario==6)h.currentMaleAnim="changed_clip";if(scenario==7)h.currentFemaleDict="changed_dict";
            if(scenario==8)h.player.Position=new Vector3(20,20,30);if(scenario==9)h.girl.Position=new Vector3(20,20,30);if(scenario==10)Function.Loaded=false;if(scenario==11)h.state=ScriptState.Idle;
            h.Step();Check(h.player.Recoveries==0&&h.girl.Recoveries==0&&Function.Stops==0,"unsafe/stale pair never restarted "+scenario);
        }
        foreach(float phase in new[]{float.NaN,float.PositiveInfinity,-2f,2f}){var h=New();h.player.Phase=phase;h.Open();h.player.Playing=false;h.girl.Phase=0.7f;h.Step();Check(!float.IsNaN(h.player.Phase)&&!float.IsInfinity(h.player.Phase)&&h.player.Phase>=0f&&h.player.Phase<=0.99f,"invalid native phase safely clamped");}
        foreach(bool female in new[]{false,true}){
            var h=New();h.player.Phase=0.2f;h.girl.Phase=0.6f;h._femaleAnimSpeedScale=2f;h.Open();Function.DeferTasks=true;Ped delayed=female?h.girl:h.player;delayed.Playing=false;h.Step();int launchedAt=Game.GameTime;
            Check(delayed.Recoveries==1&&!delayed.Playing,"asynchronous task launches once");for(int frame=0;frame<20;frame++)h.Step();
            Check(delayed.Recoveries==1,"delayed flags avoid task restart during first 500ms");Game.GameTime=launchedAt+500;h.Step();Check(delayed.Recoveries==2,"unconfirmed launch retries after 500ms");
            delayed.Playing=true;delayed.Speed=0f;if(female)delayed.Phase=0f;h.Step();
            Check(Near(delayed.Phase,female?0.6f:0.2f),"delayed native activation resumes the stored independent phase");
            Check(Near(delayed.Speed,h.animSpeed*(female?2f:1f)),"delayed native activation restores playback speed");
            delayed.Playing=false;h.Step();Check(delayed.Recoveries==3,"observed active clip clears retry latch for later loss");
        }
        {
            var h=New();h.mode=Mode.Car;h.Step();Check(Function.AllDisabled==0&&h.player.Recoveries==0,"vehicle path unchanged");
            h=New();h.animPhase=1;h.Step();Check(Function.AllDisabled==0&&h.player.Recoveries==0,"intro path unchanged");
            h=New();h.Open();h.animPhase=3;h.player.Playing=false;h.Step();Check(h.player.Recoveries==0&&!h._streetFinishGuardActive,"outro cannot return to loop");
            h=New();h.Open();h.menuLevel=MenuLevel.None;h.player.Playing=false;h.Step();Check(h.player.Recoveries==0&&!h._streetFinishGuardActive,"closed overlay releases recovery ownership");
        }
        foreach(bool controller in new[]{false,true}){
            var h=New();h._usingController=controller;h.Open(true);Check(!h._finishSelectionArmed,"held Select must release after opening Finish");h.keyCooldown=0;
            for(int repeat=0;repeat<5;repeat++){if(controller){h._menuControlCooldown=0;Function.SelectPressed=true;h.HandleControllerMenuInput();}else h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.NumPad5});h.Step();}
            Check(!h._finishExecutePending&&h.animPhase==2&&h.menuLevel==MenuLevel.Finish&&Function.Stops==0&&h.player.Outros==0,"stale Select cannot trigger real street player-only outro");
            Game.SelectHeld=false;Function.SelectHeld=false;Function.SelectPressed=false;if(!controller)h.OnKeyUp(null,new KeyEventArgs{KeyCode=Keys.NumPad5});h.UpdateFinishSelectionLatch();h.keyCooldown=0;
            Game.SelectHeld=true;Function.SelectHeld=true;if(controller){h._menuControlCooldown=0;Function.SelectPressed=true;h.HandleControllerMenuInput();}else h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.NumPad5});
            Check(h._finishExecutePending&&h.menuLevel==MenuLevel.None,"release and fresh Select schedules explicit choice");h.player.Playing=false;h.Step();
            Check(h.animPhase==3&&!h._finishExecutePending&&Function.Stops==1&&h.player.Outros==1&&h.player.Recoveries==0,"confirmed choice runs original outro without loop recovery");
        }
        {
            var h=New();h.Open();Game.SelectHeld=true;h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.NumPad5});Check(!h._finishExecutePending,"cooldown rejects immediate Select");
            h.keyCooldown=0;h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.NumPad5});Check(!h._finishExecutePending,"holding rejected Select cannot become fresh after cooldown");
            Game.SelectHeld=false;h.OnKeyUp(null,new KeyEventArgs{KeyCode=Keys.NumPad5});Game.SelectHeld=true;h.OnKeyDown(null,new KeyEventArgs{KeyCode=Keys.NumPad5});Check(h._finishExecutePending,"release/repress after cooldown accepts choice");
        }
        Console.WriteLine("PASS: "+count+" production-slice street Finish assertions; native clip loss injected, no GTA V engine validation.");
    }
}
'''
with tempfile.TemporaryDirectory(prefix='cinnamon-street-guard-tests-') as directory:
    temp = Path(directory)
    cs, dll = temp / 'StreetGuardTests.cs', temp / 'StreetGuardTests.dll'
    cs.write_text(mocks + version_declaration + master_input + region + simple + master + close_live + keyboard + controller + select_menu + scene + tests)
    rsp = temp / 'refs.rsp'
    rsp.write_text('\n'.join('/r:' + str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet), str(sdk), '/nologo', '/target:exe', '/langversion:5', '/nostdlib+',
                    '@' + str(rsp), '/out:' + str(dll), str(cs)], check=True)
    (temp / 'StreetGuardTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {
        'tfm': 'net8.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': runtime}}}))
    subprocess.run([str(dotnet), str(dll)], cwd=temp, check=True)
