#!/usr/bin/env python3
"""Render real menu methods into a native-call recorder, without GTA V.

This checks source integration and emitted text calls, not the game's font
rasterizer, safe-zone settings, duplicate installed scripts, or audio playback.
Usage: python3 tests/verify_menu_rendering.py [dotnet] [source.cs]
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'Mod/scripts/CinnamonCoffee.3.cs'
source = SOURCE.read_text(encoding='utf-8-sig')
# Preserve indices while masking braces inside comments and literals.
masked = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:[^"]|"")*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m:' '*len(m.group()), source)
def method(signature):
    start=source.index(signature); brace=masked.index('{',start); depth=1; end=brace+1
    while depth:
        if masked[end]=='{': depth+=1
        elif masked[end]=='}': depth-=1
        end+=1
    return source[start:end]
signatures = [
    'private int GetCurrentMenuItemCount()', 'private void DrawMenu()',
    'private void DispatchDrawMenu(float x, ref float y, float lh)',
    'private void DrawMainMenu(float x, ref float y, float lh)',
    'private void DrawSettingsMenu(float x, ref float y, float lh)',
    'private void DrawSectionHeader(string title, float x, ref float y)',
    'private void DrawMenuRect(float x, float y, float w, float h, int r, int g, int b, int a)',
    'private void DrawMenuText(string text, float x, float y, float w, float scale, bool centered, int r, int g, int b, int a)',
    'private void DrawMenuText(string text, float x, float y, float w, float scale, bool centered, int r, int g, int b, int a, int font)',
    'private void DrawMenuItem(string text, int itemIdx, float x, ref float y, float lh)',
    'private void DrawMenuItem(string text, int itemIdx, float x, ref float y, float lh, float scale)',
    'private void DrawMenuItemCentered(string text, int itemIdx, float x, ref float y, float lh, float scale = 0.31f)',
]
signatures += [
    'private void DrawTextOnScreen(string text, float x, float y)',
    'private void DrawTextOnScreen(string text, float x, float y, float scale, bool centered)',
]
methods='\n'.join(method(s) for s in signatures)
hud_call = re.search(r'DrawTextOnScreen\(_hudStatusText,\s*0\.5f,\s*[0-9.]+f,\s*[0-9.]+f,\s*true\);', source).group(0)
if 'private void DrawAnimationControls(' in source:
    hud_signature = re.search(r'private void DrawAnimationControls\([^)]*\)', source).group(0)
    methods += '\n' + method(hud_signature)
    hud_render = 'DrawAnimationControls("3.00x");' if 'string' in hud_signature else 'DrawAnimationControls();'
else:
    hint_start=source.index('string speedDisplay = ')
    declaration=source[hint_start:source.index(';', hint_start)+1]
    hint_if=source.index('if (showTutorialMessages)', hint_start)
    brace=masked.index('{', hint_if);depth=1;end=brace+1
    while depth:
        if masked[end]=='{':depth+=1
        elif masked[end]=='}':depth-=1
        end+=1
    hud_render=declaration+source[hint_if:end]
methods+='\nprivate void RenderHudForTest() { '+hud_render+hud_call+' }'

# Ignore unrelated panels; the actual dispatch method and real Main/Settings panels
# above are executed. Their common text/rectangle primitives remain real methods.
known={re.search(r'(\w+)\(',s).group(1) for s in signatures}
dispatch=method('private void DispatchDrawMenu(float x, ref float y, float lh)')
other_draws=sorted(set(re.findall(r'\b(Draw\w+)\(x, ref y, lh\)',dispatch))-known)
stubs='\n'.join('private void '+name+'(float x, ref float y, float lh) { }' for name in other_draws)
menu_enum=re.search(r'private enum MenuLevel \{[^}]+\}',source).group(0)
hash_names=sorted(set(re.findall(r'Hash\.([A-Z_0-9]+)',methods)))
back_methods=''
for name, signature in [('BackKeyboard','private void OnKeyDown(object sender, KeyEventArgs e)'),('BackController','private void HandleControllerMenuInput()')]:
    body=method(signature)
    branch=re.search(r'else if \(menuLevel == MenuLevel.Settings\)\s*\{([^{}]+)\}',body).group(1)
    back_methods+='private void '+name+'() {'+branch+'}\n'
main_select=method('private void HandleMenuSelect()').split('else if (menuLevel == MenuLevel.SandboxCar)',1)[0]
settings_cases=re.findall(r'case\s+(\d+):\s*// Settings[^\n]*\n\s*menuLevel = MenuLevel.Settings;\s*menuIndex = 0;\s*break;',main_select)
assert len(settings_cases)==2, 'both main Settings selection branches must exist'
main_voice_cases=re.findall(r'case\s+(\d+):\s*// Partner Voice[^\n]*\n\s*menuLevel = MenuLevel.PartnerVoices;\s*menuIndex = 0;\s*break;',main_select)
assert len(main_voice_cases)==2, 'both main voice selection branches must exist'
settings_select=method('private void HandleMenuSelect()').split('else if (menuLevel == MenuLevel.Settings)',1)[1].split('else if (menuLevel ==',1)[0]
partner_case=re.search(r'case\s+(\d+):\s*// Partner voice[^\n]*\n\s*menuLevel = MenuLevel.PartnerVoices;',settings_select)
assert partner_case, 'Settings selection must open PartnerVoices'

mocks=r'''
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
static class Function {
    public class Text { public string Value; public float X,Y,Scale,WrapLeft,WrapRight; }
    public class Rect { public float X,Y,W,H; public int R,G,B,A; }
    public static List<Text> Texts=new List<Text>(); public static List<Rect> Rects=new List<Rect>();
    static StringBuilder building=new StringBuilder(); static float scale,left,right;
    public static void Clear() { Texts.Clear(); Rects.Clear(); }
    public static void Call(Hash call,params object[] args) {
        if(call==Hash.BEGIN_TEXT_COMMAND_DISPLAY_TEXT) building.Clear();
        else if(call==Hash.ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME) building.Append((string)args[0]);
        else if(call==Hash.SET_TEXT_SCALE) scale=(float)args[0];
        else if(call==Hash.SET_TEXT_WRAP) { left=(float)args[0]; right=(float)args[1]; }
        else if(call==Hash.END_TEXT_COMMAND_DISPLAY_TEXT) Texts.Add(new Text{Value=building.ToString(),X=(float)args[0],Y=(float)args[1],Scale=scale,WrapLeft=left,WrapRight=right});
        else if(call==Hash.DRAW_RECT) Rects.Add(new Rect{X=(float)args[0],Y=(float)args[1],W=(float)args[2],H=(float)args[3],R=(int)args[4],G=(int)args[5],B=(int)args[6],A=(int)args[7]});
    }
}
class Ped { public bool Exists(){return true;} }
class Harness {
    enum Mode { None,Car,Street }
    class PartnerVoiceEntry { public string Name; }
    class ALifePedData { public string ALifeMode,Relationship; public bool HasMet,IsHooker; }
    class Telemetry { public bool IsHardDisconnected,IsConnected,IsDeviceOnline; }
    private Telemetry _telemetry=new Telemetry();
    private Dictionary<string,ALifePedData> _aLifePeds=new Dictionary<string,ALifePedData>();
    private List<PartnerVoiceEntry> _partnerVoices=new List<PartnerVoiceEntry>();
    private bool hasGirl,aLifeMode,sandboxMode,carEngineEnabled,driveableCar;
    private bool showTutorialMessages,dildoEnabled,femaleServiceVoice,femaleMoanVoice,femaleEndVoice,bjSoundsEnabled,slapSoundsEnabled,streetSitAnimEnabled,interiorLightEnabled;
    private bool _aLifeHookerServices,_sinkraCowgirlAvailable,tokenKeyboardOpen,_escalateConsented,_finishAsked;
    private bool _measuringMenu,_bjThroatPending,_throatSpeedLocked,_usingController,_liveVoiceMenu;
    private int _throatLockAt; private float animSpeed=3f;
    private string _hudStatusText="VOICE CHANGED",masterControlModifierDisplay="LB";
    private MenuLevel menuLevel; private int menuIndex,_convSelectedBranch,_intimacySelectedBranch,_leaveSelectedCluster,pingPendingTime;
    private string _currentGirlKey,deviceToken="";
    private Ped _approachCandidate; private Mode mode;
    private string[] carServiceItems=new string[2],standingServiceLabels=new string[5],sittingServiceLabels=new string[4],layingServiceLabels=new string[3];
    private const string SCRIPT_VERSION="1.1"; private const string MenuUpDisplay="UP",MenuDownDisplay="DOWN",MenuSelectDisplay="SELECT",MenuBackDisplay="BACK",MasterDisplay="J",SpeedDownDisplay="NUM4",SpeedUpDisplay="NUM6",SpeedResetDisplay="NUM1";
    private object FindBackseatVehicle(){return null;}
    private bool ShowInviteVehicleItem(){return false;}
    private bool ShowSeatSwapInActions(){return false;}
    private int GetConvSubItemCount(int index){return 0;}
    private bool IsBackseatCarMode(){return false;}
    private string GetPedFingerprint(Ped ped){return "ped";}
    private string ALifeKey(string fp){return fp;}
    private bool IsInServiceSubMenu(){return false;}
'''
tests=r'''
    static int passed,failed;
    static void Check(bool condition,string label) {
        if(condition) passed++; else { failed++; Console.WriteLine("FAIL: "+label); }
    }
    public static void Main() {
        var h=new Harness();
        foreach(bool girl in new[]{false,true}) foreach(bool life in new[]{false,true}) foreach(bool sandbox in new[]{false,true}) foreach(bool engine in new[]{false,true}) {
            h.hasGirl=girl;h.aLifeMode=life;h.sandboxMode=sandbox;h.carEngineEnabled=engine;
            h.menuLevel=MenuLevel.Main;
            Check(h.GetCurrentMenuItemCount()==(girl?10:8),"main count across modes");
            int settingsIndex=girl?MAIN_GIRL_INDEX:MAIN_NO_GIRL_INDEX;
            h.menuIndex=settingsIndex; Function.Clear(); float y=0.1f; h.DrawMainMenu(0.025f,ref y,0.034f);
            var text=Function.Texts.Single(t=>t.Value.StartsWith("Settings"));
            var highlights=Function.Rects.Where(r=>r.A==210 && r.R==79).ToList();
            Check(highlights.Count==1 && Math.Abs(highlights[0].Y-highlights[0].H/2+0.005f-text.Y)<0.0001f,"visible Settings row index matches selection dispatch across modes");
            h.menuIndex=girl?MAIN_GIRL_VOICE_INDEX:MAIN_NO_GIRL_VOICE_INDEX;Function.Clear();y=0.1f;h.DrawMainMenu(0.025f,ref y,0.034f);
            text=Function.Texts.Single(t=>t.Value.StartsWith("Partner Voice"));
            highlights=Function.Rects.Where(r=>r.A==210 && r.R==79).ToList();
            Check(highlights.Count==1 && Math.Abs(highlights[0].Y-highlights[0].H/2+0.005f-text.Y)<0.0001f,"direct Partner Voice main row matches selection dispatch across modes");
            h.menuLevel=MenuLevel.Settings;h.menuIndex=PARTNER_SETTINGS_INDEX;Function.Clear();y=0.1f;h.DrawSettingsMenu(0.025f,ref y,0.034f);
            Check(h.GetCurrentMenuItemCount()==12,"settings count across modes");
            text=Function.Texts.Single(t=>t.Value.StartsWith("Partner Voice"));
            highlights=Function.Rects.Where(r=>r.A==210 && r.R==79).ToList();
            Check(highlights.Count==1 && Math.Abs(highlights[0].Y-highlights[0].H/2+0.005f-text.Y)<0.0001f,"visible Partner Voice row matches Settings selection dispatch across modes");
            Check(text.Y<0.9f,"Partner Voice row inside viewport");
            h.BackKeyboard(); Check(h.menuLevel==MenuLevel.Main && h.menuIndex==settingsIndex,"keyboard back restores visible Settings row across modes");
            h.menuLevel=MenuLevel.Settings; h.BackController(); Check(h.menuLevel==MenuLevel.Main && h.menuIndex==settingsIndex,"controller back restores visible Settings row across modes");
        }
        h.menuLevel=MenuLevel.Settings;Function.Clear();h.DrawMenu();
        Check(Function.Texts.Count(t=>t.Value.StartsWith("Partner Voice"))==1,"one visible text draw per Partner Voice row per frame");
        Check(Function.Texts.Count(t=>t.Value=="SETTINGS")==1,"measurement pass must not emit section text");
        var duplicates=Function.Texts.GroupBy(t=>t.Value+"@"+t.X+","+t.Y).Where(g=>g.Count()>1).ToList();
        Check(duplicates.Count==0,"menu must not double-render identical text positions");
        h.showTutorialMessages=true; Function.Clear(); h.RenderHudForTest();
        Check(Function.Texts.Count==3,"HUD renders two short control rows plus one status row");
        var hudRows=Function.Texts.OrderBy(t=>t.Y).ToList();
        Check(hudRows.All(t=>t.Scale<=0.30f),"HUD uses compact text scale");
        Check(hudRows.Zip(hudRows.Skip(1),(a,b)=>b.Y-a.Y).All(gap=>gap>=0.0249f),"HUD rows have separate vertical positions");
        Console.WriteLine("Rendering checks: "+passed+" passed, "+failed+" failed. Native calls recorded; GTA rasterizer not run.");
        if(failed>0) Environment.Exit(1);
    }
}
'''.replace('MAIN_GIRL_INDEX',settings_cases[0]).replace('MAIN_NO_GIRL_INDEX',settings_cases[1]).replace('PARTNER_SETTINGS_INDEX',partner_case.group(1)).replace('MAIN_GIRL_VOICE_INDEX',main_voice_cases[0]).replace('MAIN_NO_GIRL_VOICE_INDEX',main_voice_cases[1])
dotnet=Path(sys.argv[1] if len(sys.argv)>1 else '/workspace/tools/csharp/dotnet/dotnet').resolve()
sdk=sorted((dotnet.parent/'sdk').glob('*/Roslyn/bincore/csc.dll'))[-1]
refs=sorted((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0'))[-1]
runtime=sorted((dotnet.parent/'shared/Microsoft.NETCore.App').iterdir())[-1].name
with tempfile.TemporaryDirectory(prefix='cinnamon-render-tests-') as directory:
    temp=Path(directory);cs=temp/'RenderTests.cs';dll=temp/'RenderTests.dll'
    cs.write_text('enum Hash { '+','.join(hash_names)+' }\n'+mocks+menu_enum+methods+back_methods+stubs+tests)
    # using directives must precede type declarations.
    cs.write_text(cs.read_text().replace('enum Hash { '+','.join(hash_names)+' }\n','').replace('class Ped {','enum Hash { '+','.join(hash_names)+' }\nclass Ped {',1))
    rsp=temp/'refs.rsp';rsp.write_text('\n'.join('/r:'+str(p) for p in refs.glob('*.dll')))
    subprocess.run([str(dotnet),str(sdk),'/nologo','/nowarn:0649,0414,0169','/target:exe','/langversion:5','/nostdlib+','@'+str(rsp),'/out:'+str(dll),str(cs)],check=True)
    (temp/'RenderTests.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':runtime}}}))
    subprocess.run([str(dotnet),str(dll)],cwd=temp,check=True)
