#!/usr/bin/env python3
"""Exercise the actual club region with a recorded GTA boundary, without GTA V.

Explicit club cancellation restores its actor snapshot. Full script unload uses
legacy FullReset release/unfreeze policy; the wiring check covers its club stop.
These tests cannot establish native animation alignment or interior IDs in-game.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'Mod/scripts/CinnamonCoffee.3.cs').read_text(encoding='utf-8-sig')
block=source.split('// VANILLA UNICORN DANCE MODULE',1)[1].split('// END VANILLA UNICORN DANCE MODULE',1)[0]
hashes=sorted(set(re.findall(r'Hash\.([A-Z_0-9]+)',block)))
# Check the actual frame ownership hook precedes old follow/approach processing.
on_tick=source.split('private void OnTick(',1)[1].split('private void HandleIdleState(',1)[0]
assert 'if (HandleClubFrame()) return;' in on_tick
assert on_tick.index('if (HandleClubFrame()) return;')<on_tick.index('HandleIdleState(player);')
assert source.index('TickCustomSound();',source.index('private void OnTick('))<source.index('if (HandleClubFrame()) return;',source.index('private void OnTick('))
assert re.search(r'private void FullReset\([^)]*\)\s*\{\s*StopClubDance\(false\);',source)
assert 'try { FullReset(); } catch { }' in source.split('private void OnAborted(',1)[1].split('// SETTINGS I/O',1)[0]
assert not re.search(r'\b(?:CREATE_PED|DELETE_PED|TASK_CLEAR|CLEAR_PED_TASKS|CLEAR_AREA|SET_ENTITY_VISIBLE|SET_PED_COMPONENT_VARIATION)\b',block)
mocks=r'''
using System;
using System.Collections.Generic;
struct Vector3 {
    public float X,Y,Z;
    public Vector3(float x,float y,float z){X=x;Y=y;Z=z;}
    public static Vector3 operator -(Vector3 a,Vector3 b){return new Vector3(a.X-b.X,a.Y-b.Y,a.Z-b.Z);}
    public static Vector3 operator +(Vector3 a,Vector3 b){return new Vector3(a.X+b.X,a.Y+b.Y,a.Z+b.Z);}
    public float DistanceTo(Vector3 b){Vector3 d=this-b;return (float)Math.Sqrt(d.X*d.X+d.Y*d.Y+d.Z*d.Z);}
}
enum Keys { J,F7 }
class Model {public int Hash;}
class Ped {
    public int Handle,Interior=42,Moves;public bool Valid=true,IsAlive=true,IsHuman=true,Male,IsPlayer,InVehicle,Dancing,IsPositionFrozen,IsPersistent;
    public Model Model=new Model();private Vector3 position;public float Heading;
    public Vector3 Position {get{return position;}set{position=value;Moves++;}}
    public bool Exists(){return Valid;}public bool IsInVehicle(){return InVehicle;}
    public void SetIsPersistentNoClearTask(bool value){IsPersistent=value;}
}
static class World {
    public static List<Ped> Peds=new List<Ped>();
    public static Ped[] GetNearbyPeds(Vector3 p,float radius){return Peds.FindAll(x=>x.Exists()&&x.Position.DistanceTo(p)<=radius).ToArray();}
}
class Player {public Ped Character;public int Money;}
class ScriptSettings {
    public static int Stored,Saves;public static bool FailSave;public static string LastPath;
    private int pending;
    public static ScriptSettings Load(string path){LastPath=path;return new ScriptSettings();}
    public T GetValue<T>(string section,string key,T fallback){if(section!="DanceJob"||key!="TotalTips")throw new Exception("wrong ledger key");return (T)(object)Stored;}
    public void SetValue<T>(string section,string key,T value){pending=(int)(object)value;}
    public void Save(){if(FailSave)throw new Exception("simulated save failure");Stored=pending;Saves++;}
    public static void Reset(){Stored=Saves=0;FailSave=false;LastPath=null;}
}
static class Game {public static int GameTime=1000;public static Player Player;public static bool JDown,F7Down;public static bool IsKeyPressed(Keys key){return key==Keys.J?JDown:F7Down;}}
static class Function {
    public static bool Loaded,Ready=true,BadOffset,FailScene,Disabled;public static List<int> Enabled=new List<int>();public static int ClubInterior=42,Requests,Tasks,Stops,SceneEnds;
    public static List<int> TaskActors=new List<int>(),StopActors=new List<int>();
    public static uint Key(string s){uint h=0;foreach(char c in s.ToLowerInvariant()){h+=c;h+=h<<10;h^=h>>6;}h+=h<<3;h^=h>>11;h+=h<<15;return h;}
    public static void Reset(){Loaded=BadOffset=FailScene=Disabled=false;Enabled.Clear();Ready=true;ClubInterior=42;Requests=Tasks=Stops=SceneEnds=0;TaskActors.Clear();StopActors.Clear();}
    public static void Call(Hash native,params object[] args){
        if(native==Hash.DISABLE_ALL_CONTROL_ACTIONS){Disabled=true;Enabled.Clear();}
        else if(native==Hash.ENABLE_CONTROL_ACTION)Enabled.Add((int)args[1]);
        else if(native==Hash.SET_ENTITY_COORDS_NO_OFFSET)((Ped)args[0]).Position=new Vector3((float)args[1],(float)args[2],(float)args[3]);
        else if(native==Hash.REQUEST_ANIM_DICT)Requests++;
        else if(native==Hash.TASK_SYNCHRONIZED_SCENE){var ped=(Ped)args[0];ped.Dancing=true;Tasks++;TaskActors.Add(ped.Handle);}
        else if(native==Hash.STOP_ANIM_TASK){var ped=(Ped)args[0];ped.Dancing=false;Stops++;StopActors.Add(ped.Handle);}
        else if(native==Hash.SET_SYNCHRONIZED_SCENE_LOOPED){if(!(bool)args[1])SceneEnds++;}
        else if(native==Hash.SET_SYNCHRONIZED_SCENE_PHASE){}
        else throw new Exception("unexpected side effect "+native);
    }
    public static T Call<T>(Hash native,params object[] args){object value;
        if(native==Hash.GET_HASH_KEY)value=unchecked((int)Key((string)args[0]));
        else if(native==Hash.GET_INTERIOR_AT_COORDS)value=ClubInterior;
        else if(native==Hash.GET_INTERIOR_FROM_ENTITY)value=((Ped)args[0]).Interior;
        else if(native==Hash.IS_INTERIOR_READY)value=Ready;
        else if(native==Hash.IS_PED_MALE)value=((Ped)args[0]).Male;
        else if(native==Hash.HAS_ANIM_DICT_LOADED)value=Loaded;
        else if(native==Hash.GET_ANIM_INITIAL_OFFSET_POSITION)value=BadOffset?new Vector3(float.NaN,0,0):new Vector3((float)args[2]+0.25f,(float)args[3]-0.1f,(float)args[4]+0.75f);
        else if(native==Hash.CREATE_SYNCHRONIZED_SCENE)value=FailScene?-1:7;
        else if(native==Hash.IS_ENTITY_PLAYING_ANIM)value=((Ped)args[0]).Dancing;
        else if(native==Hash.IS_DISABLED_CONTROL_PRESSED){if(!Disabled)throw new Exception("controller read before controls disabled");value=Game.JDown;}
        else throw new Exception("unexpected native read "+native);
        return (T)value;
    }
}
class Harness {
    enum ScriptState { Idle,Approaching,Animating }
    enum MenuLevel { None,Main,Club }
    private ScriptState state=ScriptState.Idle;private MenuLevel menuLevel=MenuLevel.Main;private int menuIndex;
    private Ped girl;private bool hasGirl=true,carPropActive,_streetSitPropActive,_finishExecutePending,tokenKeyboardOpen,_usingController,_suppressFinishUntilMasterReleased;
    private int _postSexPhase,keyCooldown;private const int KEY_COOLDOWN_FRAMES=20;
    private int masterControlModifier=1,masterControl=2;private Keys masterKey=Keys.J;private const string MasterDisplay="J";
    private string _hudStatusText;private int _hudStatusExpireAt;private Random rng=new Random(42);
    private void ShowHudStatus(string text,int duration){_hudStatusText=text;_hudStatusExpireAt=Game.GameTime+duration;}
    private void DrawSectionHeader(string title,float x,ref float y){}
    private void DrawMenuItem(string text,int index,float x,ref float y,float lh,float scale=0.31f){}
    private void DrawTextOnScreen(string text,float x,float y,float scale,bool centered){}
    private void DrawMenuText(string text,float x,float y,float w,float scale,bool centered,int r,int g,int b,int a){}
    private void HandleControllerMenuInput(){}private void DrawMenu(){}
'''
tests=r'''
    static int checks;
    static void Check(bool condition,string label){checks++;if(!condition)throw new Exception("FAIL "+label);}
    static bool Same(Vector3 a,Vector3 b){return a.DistanceTo(b)<0.001f;}
    static Harness New(){
        Function.Reset();ScriptSettings.Reset();World.Peds.Clear();Game.GameTime=1000;Game.JDown=Game.F7Down=false;
        var h=new Harness();
        var player=new Ped{Handle=1,IsPlayer=true,Male=false,Position=CLUB_INTERIOR_PROBE,Heading=12f};
        player.Model.Hash=unchecked((int)Function.Key("mp_f_freemode_01"));
        Game.Player=new Player{Character=player,Money=0};
        h.girl=new Ped{Handle=2,Position=CLUB_INTERIOR_PROBE+new Vector3(0.5f,0,0),Heading=87f,IsPositionFrozen=true,IsPersistent=false};
        player.Moves=h.girl.Moves=0;World.Peds.Add(player);World.Peds.Add(h.girl);return h;
    }
    static void Perform(Harness h,bool playerJob=false){h.StartClubDance(playerJob);Function.Loaded=true;h.TickClubDance();Check(h._clubPhase==ClubDancePhase.Performing,"requested club performance starts after animation load");}
    public static void Main(){
        var h=New();var original=h.girl.Position;float heading=h.girl.Heading;var playerPosition=Game.Player.Character.Position;
        h.StartClubDance(false);
        Check(h._clubPhase==ClubDancePhase.Loading&&Function.Requests==1,"start enters pending animation-loading phase");
        Check(h.girl.Moves==0&&h.girl.IsPositionFrozen&&!h.girl.IsPersistent,"pending load changes no actor position or ownership flags");
        Function.Loaded=true;h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Performing&&Function.Tasks==1&&Function.TaskActors[0]==2,"loaded partner joins only its scene");
        Check(!h.girl.IsPositionFrozen&&h.girl.IsPersistent,"performance applies temporary actor flags");
        Check(Same(Game.Player.Character.Position,playerPosition)&&Game.Player.Character.Moves==0,"partner performance leaves player position untouched");
        h.StopClubDance(true);
        Check(h._clubPhase==ClubDancePhase.Off&&Same(h.girl.Position,original)&&h.girl.Heading==heading,"explicit stop restores partner location and heading");
        Check(h.girl.IsPositionFrozen&&!h.girl.IsPersistent&&Function.Stops==1&&Function.StopActors[0]==2,"explicit stop restores original flags and stops only owned actor clip");
        int stops=Function.Stops;h.StopClubDance(true);Check(Function.Stops==stops,"repeated stop is idempotent");

        h=New();h.StartClubDance(false);Game.GameTime=5999;h.TickClubDance();Check(h._clubPhase==ClubDancePhase.Loading,"load timeout is bounded without premature cancellation");
        Game.GameTime=6000;h.TickClubDance();Check(h._clubPhase==ClubDancePhase.Off&&h.girl.Moves==0&&Function.Tasks==0,"missing animation times out without stage teleport fallback");
        h=New();Function.BadOffset=true;PerformInvalid(h);
        h=New();Function.FailScene=true;original=h.girl.Position;h.StartClubDance(false);Function.Loaded=true;h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Off&&Same(h.girl.Position,original)&&h.girl.IsPositionFrozen&&!h.girl.IsPersistent,"failed scene creation rolls back placement and flags");

        h=New();Game.Player.Character.Interior=43;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off&&Function.Requests==0,"other interior rejects club start");
        h=New();Function.ClubInterior=0;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"unknown interior rejects club start");
        h=New();Function.Ready=false;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"unready interior rejects club start");
        h=New();Game.Player.Character.Position=new Vector3(0,0,0);h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"distant player cannot start remotely");
        h=New();Game.Player.Character.InVehicle=true;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"vehicle start is rejected");
        h=New();h.state=ScriptState.Animating;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"core animation cannot overlap club performance");
        h=New();h.state=ScriptState.Approaching;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"core approach cannot overlap club performance");
        h=New();h.carPropActive=true;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"car proposition transition blocks club start");
        h=New();h._postSexPhase=1;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"pending finish speech blocks club start");
        h=New();h.hasGirl=false;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"missing partner blocks partner show");
        h=New();h.girl.Male=true;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"male actor rejected");
        h=New();h.girl.IsHuman=false;h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off,"nonhuman actor rejected");
        h=New();Game.Player.Character.Model.Hash=123;h.StartClubDance(true);Check(h._clubPhase==ClubDancePhase.Off,"dance job requires exact MP Female model");

        h=New();foreach(var pole in CLUB_POLES)World.Peds.Add(new Ped{Handle=10+World.Peds.Count,Position=pole,Male=true});
        h.StartClubDance(false);Check(h._clubPhase==ClubDancePhase.Off&&Function.Tasks==0&&Function.Stops==0&&World.Peds.Count==5,"occupied poles block start without changing or removing existing NPCs");
        h=New();h.StartClubDance(false);World.Peds.Add(new Ped{Handle=30,Position=CLUB_POLES[h._clubPole],Male=true});Function.Loaded=true;h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Off&&h.girl.Moves==0&&Function.Tasks==0,"pole occupied during loading cancels before placement");

        h=New();Perform(h);var stage=h.girl.Position;Game.Player.Character.Interior=43;h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Off&&Same(h.girl.Position,stage)&&h.girl.IsPositionFrozen&&!h.girl.IsPersistent,"leaving club restores flags without teleporting actor back");
        h=New();Perform(h);stage=h.girl.Position;h.girl.IsAlive=false;h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Off&&Same(h.girl.Position,stage)&&h.girl.IsPositionFrozen&&!h.girl.IsPersistent,"actor death ends scene without resurrecting or moving actor");
        h=New();Perform(h);h.girl.Valid=false;h.girl=new Ped{Handle=55,Position=CLUB_INTERIOR_PROBE};h.TickClubDance();
        Check(h._clubPhase==ClubDancePhase.Off&&h.girl.Moves==1&&!h.girl.IsPersistent,"replacement actor receives no old snapshot");
        h=New();Perform(h);h.girl.Dancing=false;Game.GameTime=2001;h.TickClubDance();Check(h._clubPhase==ClubDancePhase.Off,"interrupted own animation ends performance");

        h=New();original=Game.Player.Character.Position;Game.Player.Character.IsPositionFrozen=true;Game.Player.Character.IsPersistent=false;Perform(h,true);
        Check(h._clubPerformer.Handle==1&&!Game.Player.Character.IsPositionFrozen&&Game.Player.Character.IsPersistent,"MP Female player becomes performer with captured flags");
        var spectator=new Ped{Handle=75,Male=true,Position=Game.Player.Character.Position+new Vector3(3f,0,0)};World.Peds.Add(spectator);
        Game.GameTime=30999;h.TickClubDance();Check(ScriptSettings.Stored==0&&ScriptSettings.Saves==0,"no ledger credit before thirty-second interval");
        Game.GameTime=31000;h.TickClubDance();int firstTip=ScriptSettings.Stored;Check(firstTip>=10&&firstTip<=50&&h._clubEarned==firstTip&&ScriptSettings.Saves==1,"nearby existing audience awards bounded persisted club tip");
        Check(Game.Player.Money==0,"MP Female tip never claims unsupported story-mode wallet credit");
        for(int i=0;i<200;i++)h.TickClubDance();Check(ScriptSettings.Stored==firstTip&&ScriptSettings.Saves==1,"same-frame repeated ticks cannot farm ledger credits");
        Game.GameTime=91000;h.TickClubDance();Check(ScriptSettings.Stored-firstTip>=10&&ScriptSettings.Stored-firstTip<=50&&ScriptSettings.Saves==2,"skipped frames produce one recorded tip rather than catch-up farming");
        Check(World.Peds.Contains(spectator)&&spectator.Moves==1&&!spectator.IsPersistent,"spectator remains an untouched existing world NPC");
        h.StopClubDance(true);Check(Same(Game.Player.Character.Position,original)&&Game.Player.Character.IsPositionFrozen&&!Game.Player.Character.IsPersistent,"normal player stop restores captured position and flags");
        h=New();Perform(h,true);Game.GameTime=31000;h.TickClubDance();Check(ScriptSettings.Stored==0&&ScriptSettings.Saves==0,"no audience means no recorded tip");
        h=New();Perform(h,true);World.Peds.Add(new Ped{Handle=76,Male=true,Interior=43,Position=Game.Player.Character.Position+new Vector3(3f,0,0)});Game.GameTime=31000;h.TickClubDance();Check(ScriptSettings.Stored==0&&ScriptSettings.Saves==0,"spectator in another interior cannot tip");

        h=New();h.OpenClubMenu();Check(h.menuLevel==MenuLevel.Club,"club menu opens inside venue");h.menuIndex=4;h.HandleClubSelect();Check(h.menuLevel==MenuLevel.None,"menu close button returns control without starting performance");
        h=New();Perform(h);h.menuIndex=2;h.HandleClubSelect();Check(h._clubDanceVariant==1,"variant cannot change mid-performance");
        h.menuLevel=MenuLevel.None;Game.F7Down=true;Check(h.HandleClubFrame()&&h.menuLevel==MenuLevel.Club,"F7 reopens club menu while scene remains owned");
        Game.F7Down=false;Game.JDown=true;h.keyCooldown=0;Check(h.HandleClubFrame()&&h._clubPhase==ClubDancePhase.Off,"J ends only club show and consumes frame");
        h.menuLevel=MenuLevel.None;for(int i=0;i<40;i++){h.keyCooldown=0;Check(h.HandleClubFrame(),"held J cannot leak into core handler frame "+i);}
        Game.JDown=false;Check(!h.HandleClubFrame(),"releasing J returns subsequent idle frame to core handler");
        h=New();Perform(h);h._usingController=true;Check(h.HandleClubFrame(),"controller club show owns its frame");
        Check(Function.Enabled.Contains(1)&&Function.Enabled.Contains(2)&&Function.Enabled.Contains(30)&&Function.Enabled.Contains(31),"watching player retains camera and walking controls after all menu handling");
        h=New();Perform(h,true);h._usingController=true;Check(h.HandleClubFrame(),"controller dance job owns its frame");
        Check(Function.Enabled.Contains(1)&&Function.Enabled.Contains(2)&&!Function.Enabled.Contains(30)&&!Function.Enabled.Contains(31),"dancing player retains camera while movement stays blocked");
        h=New();ScriptSettings.Stored=1234;h.OpenClubMenu();Check(h._clubCareerTips==1234&&ScriptSettings.Saves==0,"opening menu reloads stored career tips without creating credits");
        h=New();ScriptSettings.Stored=-100;h.CreditClubTip(10);Check(ScriptSettings.Stored==10&&h._clubCareerTips==10,"negative persisted balance is clamped before credit");
        var restarted=new Harness();restarted.CreditClubTip(20);Check(ScriptSettings.Stored==30&&restarted._clubCareerTips==30,"new module instance credits previously saved ledger balance");
        ScriptSettings.Stored=int.MaxValue-2;restarted._clubEarned=int.MaxValue-2;restarted.CreditClubTip(50);
        Check(ScriptSettings.Stored==int.MaxValue&&restarted._clubCareerTips==int.MaxValue&&restarted._clubEarned==int.MaxValue,"record and shift earnings clamp without integer overflow");
        h=New();ScriptSettings.Stored=42;ScriptSettings.FailSave=true;h.CreditClubTip(10);
        Check(ScriptSettings.Stored==42&&ScriptSettings.Saves==0&&h._hudStatusText.Contains("COULD NOT BE SAVED"),"ledger save failure keeps persisted value and reports failure");
        Console.WriteLine("Club dance: "+checks+" state/cleanup/gating/tip checks passed; GTA native boundary simulated.");
    }
    private static void PerformInvalid(Harness h){h.StartClubDance(false);Function.Loaded=true;h.TickClubDance();Check(h._clubPhase==ClubDancePhase.Off&&h.girl.Moves==0&&Function.Tasks==0,"invalid animation offset cancels without placement");}
}
'''
dotnet=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk=sorted((dotnet.parent/'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs=sorted((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime=sorted((dotnet.parent/'shared/Microsoft.NETCore.App').iterdir())[-1].name
with tempfile.TemporaryDirectory(prefix='cinnamon-club-tests-') as directory:
    temp=Path(directory);cs=temp/'ClubTests.cs';dll=temp/'ClubTests.dll'
    cs.write_text(mocks.replace('static class Function {','enum Hash {'+','.join(hashes)+'}\nstatic class Function {')+block+tests)
    rsp=temp/'refs.rsp';rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/nowarn:0649,0414,0169','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'ClubTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
print('Club hook and unload wiring checks passed; native alignment and live GTA behavior remain unverified.')
