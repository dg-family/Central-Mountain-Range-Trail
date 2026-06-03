#!/usr/bin/env python3
"""
GPX to JSON Converter
將GPX檔案中的trkpt標籤轉換為JSON格式
"""

import xml.etree.ElementTree as ET
import json
import re
from typing import List, Dict, Any

def extract_trkpt_from_gpx_file(file_path: str) -> List[Dict[str, float]]:
    """
    從GPX檔案中提取所有trkpt座標點
    
    Args:
        file_path: GPX檔案路徑
        
    Returns:
        包含lat和lon的字典列表
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # 處理XML命名空間
        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['gpx'] = namespace
            trkpt_tag = f"{{{namespace}}}trkpt"
        else:
            trkpt_tag = "trkpt"
        
        coordinates = []
        
        # 找到所有trkpt元素
        for trkpt in root.iter(trkpt_tag):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            coordinates.append({"lat": lat, "lon": lon})
            
        return coordinates
        
    except Exception as e:
        print(f"錯誤處理檔案 {file_path}: {e}")
        return []

def extract_trkpt_from_gpx_string(gpx_content: str) -> List[Dict[str, float]]:
    """
    從GPX字串內容中提取所有trkpt座標點
    
    Args:
        gpx_content: GPX XML字串內容
        
    Returns:
        包含lat和lon的字典列表
    """
    try:
        root = ET.fromstring(gpx_content)
        
        # 處理XML命名空間
        namespaces = {}
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0][1:]
            namespaces['gpx'] = namespace
            trkpt_tag = f"{{{namespace}}}trkpt"
        else:
            trkpt_tag = "trkpt"
        
        coordinates = []
        
        # 找到所有trkpt元素
        for trkpt in root.iter(trkpt_tag):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            coordinates.append({"lat": lat, "lon": lon})
            
        return coordinates
        
    except Exception as e:
        print(f"錯誤處理GPX字串: {e}")
        return []

def extract_trkpt_with_regex(gpx_content: str) -> List[Dict[str, float]]:
    """
    使用正則表達式從GPX內容中提取trkpt座標
    這個方法可以處理格式不規範的GPX內容
    
    Args:
        gpx_content: GPX內容字串
        
    Returns:
        包含lat和lon的字典列表
    """
    coordinates = []
    
    # 正則表達式匹配trkpt標籤中的lat和lon屬性
    pattern = r'<trkpt\s+lat="([^"]+)"\s+lon="([^"]+)"[^>]*/?>'
    matches = re.findall(pattern, gpx_content)
    
    for lat_str, lon_str in matches:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            coordinates.append({"lat": lat, "lon": lon})
        except ValueError:
            print(f"無法轉換座標: lat={lat_str}, lon={lon_str}")
            continue
    
    return coordinates

def save_coordinates_to_json(coordinates: List[Dict[str, float]], output_file: str):
    """
    將座標列表儲存為JSON檔案
    
    Args:
        coordinates: 座標列表
        output_file: 輸出檔案路徑
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(coordinates, f, ensure_ascii=False, indent=2)
        print(f"座標已儲存到: {output_file}")
        print(f"總共轉換了 {len(coordinates)} 個座標點")
    except Exception as e:
        print(f"儲存檔案時發生錯誤: {e}")

def main():
    """主程式"""
    print("GPX to JSON 轉換器")
    print("=" * 40)
    
    # 處理現有的GPX檔案
    gpx_file = "/workspace/siyuan_pass_trail.gpx"
    print(f"\n處理現有GPX檔案: {gpx_file}")
    coordinates_from_file = extract_trkpt_from_gpx_file(gpx_file)
    
    if coordinates_from_file:
        save_coordinates_to_json(coordinates_from_file, "/workspace/siyuan_coordinates.json")
        print(f"從檔案提取了 {len(coordinates_from_file)} 個座標點")
        
        # 顯示前5個座標點作為範例
        print("\n前5個座標點範例:")
        for i, coord in enumerate(coordinates_from_file[:5]):
            print(f"  {i+1}. {coord}")
    
    # 用戶提供的GPX字串內容
    user_gpx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" version="1.1" creator="overpass-turbo"><metadata><desc>Filtered OSM data converted to GPX by overpass turbo</desc><copyright author="The data included in this document is from www.openstreetmap.org. The data is made available under ODbL."/><time>2025-08-27T08:06:11Z</time></metadata><trk><name>820 林道</name><desc>highway=track
motorcar=no
name=820 林道</desc><link href="http://osm.org/browse/way/334667980"/><trkseg><trkpt lat="24.2045806" lon="121.3402436"/><trkpt lat="24.2042188" lon="121.3404172"/><trkpt lat="24.2041042" lon="121.3404903"/><trkpt lat="24.2039571" lon="121.3405111"/><trkpt lat="24.2038585" lon="121.3404906"/><trkpt lat="24.2037369" lon="121.3405099"/><trkpt lat="24.2036758" lon="121.3405597"/><trkpt lat="24.2034646" lon="121.3405761"/><trkpt lat="24.2033636" lon="121.3405412"/><trkpt lat="24.2032961" lon="121.3404714"/><trkpt lat="24.2032956" lon="121.3404353"/><trkpt lat="24.2032574" lon="121.3403682"/><trkpt lat="24.2032363" lon="121.3403546"/><trkpt lat="24.2032319" lon="121.3403296"/><trkpt lat="24.2032818" lon="121.3402984"/><trkpt lat="24.2033291" lon="121.3401944"/><trkpt lat="24.2034789" lon="121.3400914"/><trkpt lat="24.2037964" lon="121.3399773"/><trkpt lat="24.2038738" lon="121.3399286"/><trkpt lat="24.2040017" lon="121.3398855"/><trkpt lat="24.2040095" lon="121.3398632"/><trkpt lat="24.2040068" lon="121.3398055"/><trkpt lat="24.2040035" lon="121.3397581"/><trkpt lat="24.2039742" lon="121.3397549"/><trkpt lat="24.2035557" lon="121.3396025"/><trkpt lat="24.2033918" lon="121.3394898"/><trkpt lat="24.2032481" lon="121.3393585"/><trkpt lat="24.2032326" lon="121.3392964"/><trkpt lat="24.2032455" lon="121.3392362"/><trkpt lat="24.2033564" lon="121.3389341"/><trkpt lat="24.2035418" lon="121.3388975"/><trkpt lat="24.2036231" lon="121.338889"/><trkpt lat="24.2037493" lon="121.3388878"/><trkpt lat="24.2040117" lon="121.3390251"/><trkpt lat="24.2040886" lon="121.339019"/><trkpt lat="24.2043312" lon="121.338948"/><trkpt lat="24.2045294" lon="121.3389078"/><trkpt lat="24.2047397" lon="121.3388568"/><trkpt lat="24.2049043" lon="121.338747"/><trkpt lat="24.2049863" lon="121.3386857"/><trkpt lat="24.2050361" lon="121.3386038"/><trkpt lat="24.2050053" lon="121.3384726"/><trkpt lat="24.2050011" lon="121.3383634"/><trkpt lat="24.2049603" lon="121.3382138"/><trkpt lat="24.2049969" lon="121.3379153"/><trkpt lat="24.2050358" lon="121.3377706"/><trkpt lat="24.2050484" lon="121.3375983"/><trkpt lat="24.2050168" lon="121.3373796"/><trkpt lat="24.204929" lon="121.3372396"/><trkpt lat="24.2048111" lon="121.3371528"/><trkpt lat="24.2046003" lon="121.3371105"/><trkpt lat="24.2044644" lon="121.3370034"/><trkpt lat="24.2043495" lon="121.3368729"/><trkpt lat="24.2042844" lon="121.3367104"/><trkpt lat="24.2043593" lon="121.3365429"/><trkpt lat="24.2045931" lon="121.3363188"/><trkpt lat="24.2046287" lon="121.3362067"/><trkpt lat="24.2046861" lon="121.3361463"/><trkpt lat="24.2048639" lon="121.3360756"/><trkpt lat="24.204919" lon="121.3360169"/><trkpt lat="24.2049609" lon="121.3359471"/><trkpt lat="24.2049892" lon="121.3359246"/><trkpt lat="24.2050008" lon="121.3358727"/><trkpt lat="24.2050062" lon="121.3358217"/><trkpt lat="24.2049651" lon="121.3356889"/><trkpt lat="24.2049433" lon="121.335654"/><trkpt lat="24.2049374" lon="121.3355198"/><trkpt lat="24.2048804" lon="121.3352706"/><trkpt lat="24.2048624" lon="121.3350816"/><trkpt lat="24.2049281" lon="121.3349998"/><trkpt lat="24.2049452" lon="121.3349354"/><trkpt lat="24.2052706" lon="121.3347208"/><trkpt lat="24.2053191" lon="121.3345965"/><trkpt lat="24.2053122" lon="121.3344043"/><trkpt lat="24.2051825" lon="121.334281"/><trkpt lat="24.2050431" lon="121.3342139"/><trkpt lat="24.2048009" lon="121.3341817"/><trkpt lat="24.2046957" lon="121.33412"/><trkpt lat="24.2046492" lon="121.3340342"/><trkpt lat="24.2046289" lon="121.3338237"/><trkpt lat="24.2046612" lon="121.333758"/><trkpt lat="24.2046644" lon="121.3336469"/><trkpt lat="24.2046898" lon="121.3334643"/><trkpt lat="24.2047323" lon="121.3333535"/><trkpt lat="24.2047286" lon="121.3331217"/><trkpt lat="24.2046605" lon="121.332972"/><trkpt lat="24.2044935" lon="121.3328265"/><trkpt lat="24.2044935" lon="121.3327031"/><trkpt lat="24.2045033" lon="121.3326361"/><trkpt lat="24.204549" lon="121.3324827"/><trkpt lat="24.2045352" lon="121.3323498"/><trkpt lat="24.2044859" lon="121.3323304"/><trkpt lat="24.2044231" lon="121.3323349"/><trkpt lat="24.204308" lon="121.3324249"/><trkpt lat="24.2042566" lon="121.3324865"/><trkpt lat="24.2042244" lon="121.3326091"/><trkpt lat="24.2041147" lon="121.3326708"/><trkpt lat="24.2040751" lon="121.3326777"/><trkpt lat="24.2040068" lon="121.332664"/><trkpt lat="24.2039862" lon="121.3326313"/><trkpt lat="24.2039178" lon="121.3325671"/><trkpt lat="24.2038212" lon="121.3325563"/><trkpt lat="24.2037399" lon="121.3325547"/><trkpt lat="24.2036842" lon="121.3325998"/><trkpt lat="24.2036134" lon="121.3326166"/><trkpt lat="24.2031771" lon="121.3325349"/><trkpt lat="24.2029043" lon="121.3325713"/><trkpt lat="24.202759" lon="121.3325368"/><trkpt lat="24.202671" lon="121.3324644"/><trkpt lat="24.2025878" lon="121.3323651"/><trkpt lat="24.2024263" lon="121.3323008"/><trkpt lat="24.2023015" lon="121.3321774"/><trkpt lat="24.2022184" lon="121.3320835"/><trkpt lat="24.202096" lon="121.3320406"/><trkpt lat="24.2019641" lon="121.3319665"/><trkpt lat="24.2019339" lon="121.3319115"/><trkpt lat="24.2019737" lon="121.3317831"/><trkpt lat="24.2019908" lon="121.331708"/><trkpt lat="24.2021597" lon="121.3315498"/><trkpt lat="24.2021645" lon="121.3313781"/><trkpt lat="24.2022184" lon="121.3312949"/><trkpt lat="24.2023162" lon="121.3311877"/><trkpt lat="24.2024434" lon="121.3311179"/><trkpt lat="24.2025609" lon="121.331067"/><trkpt lat="24.2026538" lon="121.3310053"/><trkpt lat="24.202742" lon="121.3308342"/><trkpt lat="24.2027606" lon="121.3307569"/><trkpt lat="24.2027683" lon="121.3306524"/><trkpt lat="24.202722" lon="121.330514"/><trkpt lat="24.2026293" lon="121.330458"/><trkpt lat="24.2025322" lon="121.3303711"/><trkpt lat="24.2024603" lon="121.3302224"/><trkpt lat="24.2024287" lon="121.3301122"/><trkpt lat="24.2024034" lon="121.3299838"/><trkpt lat="24.2024088" lon="121.3298309"/><trkpt lat="24.2024344" lon="121.3297888"/><trkpt lat="24.20256" lon="121.3297069"/><trkpt lat="24.2027004" lon="121.3295891"/><trkpt lat="24.202796" lon="121.3294754"/><trkpt lat="24.2027362" lon="121.3293866"/><trkpt lat="24.2026407" lon="121.3293669"/><trkpt lat="24.2026184" lon="121.3293407"/><trkpt lat="24.2024343" lon="121.3293621"/><trkpt lat="24.202352" lon="121.3293476"/><trkpt lat="24.2021862" lon="121.3292862"/><trkpt lat="24.2020733" lon="121.3292627"/><trkpt lat="24.2018209" lon="121.3292374"/><trkpt lat="24.2017369" lon="121.3292506"/><trkpt lat="24.201619" lon="121.3291997"/><trkpt lat="24.2015412" lon="121.3291355"/><trkpt lat="24.2014798" lon="121.3290609"/><trkpt lat="24.2014356" lon="121.3290271"/><trkpt lat="24.2013832" lon="121.3290011"/><trkpt lat="24.2013029" lon="121.3290086"/><trkpt lat="24.201225" lon="121.3289621"/><trkpt lat="24.2011642" lon="121.3289555"/><trkpt lat="24.2011316" lon="121.3289818"/><trkpt lat="24.2010546" lon="121.328984"/><trkpt lat="24.2010145" lon="121.3289419"/><trkpt lat="24.2009772" lon="121.328916"/><trkpt lat="24.200947" lon="121.3289281"/><trkpt lat="24.2008866" lon="121.3288974"/><trkpt lat="24.2008569" lon="121.3288631"/><trkpt lat="24.2008003" lon="121.3288547"/><trkpt lat="24.2006838" lon="121.3288702"/><trkpt lat="24.2005933" lon="121.328833"/><trkpt lat="24.2005583" lon="121.3288084"/><trkpt lat="24.2005521" lon="121.3287615"/><trkpt lat="24.2004838" lon="121.3286807"/><trkpt lat="24.2004046" lon="121.3286271"/><trkpt lat="24.2003497" lon="121.3285404"/><trkpt lat="24.2003124" lon="121.3284489"/><trkpt lat="24.2001731" lon="121.3283499"/><trkpt lat="24.2000386" lon="121.3283096"/><trkpt lat="24.1999187" lon="121.3281997"/><trkpt lat="24.1999064" lon="121.3281031"/><trkpt lat="24.1999236" lon="121.3279154"/><trkpt lat="24.2000043" lon="121.3278054"/><trkpt lat="24.2001295" lon="121.3276829"/><trkpt lat="24.20027" lon="121.327611"/><trkpt lat="24.2002881" lon="121.3275586"/><trkpt lat="24.2002832" lon="121.3274862"/><trkpt lat="24.2002441" lon="121.3274111"/><trkpt lat="24.200134" lon="121.3273494"/><trkpt lat="24.2001046" lon="121.327277"/><trkpt lat="24.2001315" lon="121.3272073"/><trkpt lat="24.2001756" lon="121.3271724"/><trkpt lat="24.2002857" lon="121.3271402"/><trkpt lat="24.2003615" lon="121.3270839"/><trkpt lat="24.2004691" lon="121.3269927"/><trkpt lat="24.2005548" lon="121.3268505"/><trkpt lat="24.200611" lon="121.3267137"/><trkpt lat="24.2006331" lon="121.3266252"/><trkpt lat="24.2005772" lon="121.3265779"/><trkpt lat="24.2005226" lon="121.3265602"/><trkpt lat="24.200337" lon="121.3264616"/><trkpt lat="24.2002025" lon="121.3264214"/><trkpt lat="24.200112" lon="121.3262739"/><trkpt lat="24.1998869" lon="121.3261102"/><trkpt lat="24.1997621" lon="121.3260003"/><trkpt lat="24.1996936" lon="121.3259037"/><trkpt lat="24.199559" lon="121.3257884"/><trkpt lat="24.1995297" lon="121.3257186"/><trkpt lat="24.1994514" lon="121.3256301"/><trkpt lat="24.1993584" lon="121.3254772"/><trkpt lat="24.1993168" lon="121.3252519"/><trkpt lat="24.1993462" lon="121.3251446"/><trkpt lat="24.1994832" lon="121.325091"/><trkpt lat="24.1997058" lon="121.3249837"/><trkpt lat="24.1998624" lon="121.3249462"/><trkpt lat="24.1999701" lon="121.3249113"/><trkpt lat="24.2000801" lon="121.3248684"/><trkpt lat="24.2002783" lon="121.3248684"/><trkpt lat="24.2003542" lon="121.3248228"/><trkpt lat="24.2004153" lon="121.3247825"/><trkpt lat="24.2005303" lon="121.3246672"/><trkpt lat="24.2006159" lon="121.3245197"/><trkpt lat="24.2007113" lon="121.3243748"/><trkpt lat="24.2007407" lon="121.3242139"/><trkpt lat="24.2006649" lon="121.3238974"/><trkpt lat="24.2005792" lon="121.3238009"/><trkpt lat="24.2004104" lon="121.3236587"/><trkpt lat="24.200337" lon="121.3235407"/><trkpt lat="24.2002563" lon="121.3233422"/><trkpt lat="24.2001633" lon="121.3232295"/><trkpt lat="24.2001315" lon="121.3231008"/><trkpt lat="24.200112" lon="121.3227682"/><trkpt lat="24.200019" lon="121.3226475"/><trkpt lat="24.1999798" lon="121.3225134"/><trkpt lat="24.2000019" lon="121.3223659"/><trkpt lat="24.2000581" lon="121.3221647"/><trkpt lat="24.2002066" lon="121.3221313"/><trkpt lat="24.2003955" lon="121.3221022"/><trkpt lat="24.2006722" lon="121.3219957"/><trkpt lat="24.2008679" lon="121.3218536"/><trkpt lat="24.2011028" lon="121.3217838"/><trkpt lat="24.2012845" lon="121.3217751"/><trkpt lat="24.2013823" lon="121.3217802"/><trkpt lat="24.2015559" lon="121.3218127"/><trkpt lat="24.2017441" lon="121.3218261"/><trkpt lat="24.2020496" lon="121.3217312"/><trkpt lat="24.2021711" lon="121.321678"/><trkpt lat="24.2022943" lon="121.3215251"/><trkpt lat="24.2022891" lon="121.3213103"/><trkpt lat="24.2022658" lon="121.3211724"/><trkpt lat="24.2022503" lon="121.3210465"/><trkpt lat="24.2020919" lon="121.3206464"/><trkpt lat="24.2020314" lon="121.320529"/><trkpt lat="24.202014" lon="121.320432"/><trkpt lat="24.2020686" lon="121.3202702"/><trkpt lat="24.2022084" lon="121.3201715"/><trkpt lat="24.2023146" lon="121.3201158"/><trkpt lat="24.2024816" lon="121.3199672"/><trkpt lat="24.202595" lon="121.3198821"/><trkpt lat="24.2027855" lon="121.3194673"/><trkpt lat="24.2029247" lon="121.3193949"/><trkpt lat="24.203128" lon="121.319338"/><trkpt lat="24.2032488" lon="121.319338"/><trkpt lat="24.2033569" lon="121.3193029"/><trkpt lat="24.2035281" lon="121.3191688"/><trkpt lat="24.2037023" lon="121.3188849"/><trkpt lat="24.2038358" lon="121.3185826"/><trkpt lat="24.2039243" lon="121.3184481"/><trkpt lat="24.2041888" lon="121.3182907"/><trkpt lat="24.2042581" lon="121.3182098"/><trkpt lat="24.2042798" lon="121.3180362"/><trkpt lat="24.2043237" lon="121.3179538"/><trkpt lat="24.204368" lon="121.3175624"/><trkpt lat="24.2042851" lon="121.3174321"/><trkpt lat="24.2040536" lon="121.3173213"/><trkpt lat="24.2038833" lon="121.317373"/><trkpt lat="24.203715" lon="121.3174356"/><trkpt lat="24.203567" lon="121.3174794"/><trkpt lat="24.2032161" lon="121.3174896"/><trkpt lat="24.203109" lon="121.3174726"/><trkpt lat="24.2030018" lon="121.3174266"/><trkpt lat="24.202901" lon="121.317425"/><trkpt lat="24.2027756" lon="121.3175093"/><trkpt lat="24.2026747" lon="121.3176115"/><trkpt lat="24.2025753" lon="121.3177511"/><trkpt lat="24.2024883" lon="121.3179243"/><trkpt lat="24.2024246" lon="121.3180086"/><trkpt lat="24.202328" lon="121.3181049"/><trkpt lat="24.2020675" lon="121.3182749"/><trkpt lat="24.2018917" lon="121.3182915"/><trkpt lat="24.2016567" lon="121.3182915"/><trkpt lat="24.201445" lon="121.3182313"/><trkpt lat="24.2013615" lon="121.3182573"/><trkpt lat="24.2012637" lon="121.3183288"/><trkpt lat="24.2011271" lon="121.3183798"/><trkpt lat="24.2008256" lon="121.3186391"/><trkpt lat="24.2007622" lon="121.3187254"/><trkpt lat="24.2006551" lon="121.3188088"/><trkpt lat="24.2004156" lon="121.3189466"/><trkpt lat="24.2003474" lon="121.3190419"/><trkpt lat="24.2002773" lon="121.3190542"/><trkpt lat="24.2001713" lon="121.3190807"/><trkpt lat="24.2000418" lon="121.3191433"/><trkpt lat="24.1997826" lon="121.3192236"/><trkpt lat="24.199634" lon="121.3190597"/><trkpt lat="24.199514" lon="121.3189941"/><trkpt lat="24.1992285" lon="121.3187085"/><trkpt lat="24.1991538" lon="121.3186496"/><trkpt lat="24.199077" lon="121.3186192"/><trkpt lat="24.1989271" lon="121.3185978"/><trkpt lat="24.1987811" lon="121.3185352"/><trkpt lat="24.1985845" lon="121.3185147"/><trkpt lat="24.1985033" lon="121.3184895"/><trkpt lat="24.1984674" lon="121.3184668"/><trkpt lat="24.1984467" lon="121.3184913"/><trkpt lat="24.1983724" lon="121.318551"/><trkpt lat="24.1983439" lon="121.3185567"/><trkpt lat="24.1983181" lon="121.3185438"/><trkpt lat="24.1982637" lon="121.3184162"/><trkpt lat="24.1982243" lon="121.3183665"/><trkpt lat="24.1979888" lon="121.3183935"/><trkpt lat="24.1978493" lon="121.3183392"/><trkpt lat="24.1974702" lon="121.3181547"/><trkpt lat="24.1973438" lon="121.3182394"/><trkpt lat="24.1972515" lon="121.3183658"/><trkpt lat="24.1971824" lon="121.3185031"/><trkpt lat="24.1971523" lon="121.3186182"/><trkpt lat="24.1970868" lon="121.3187257"/><trkpt lat="24.1970287" lon="121.3187691"/><trkpt lat="24.1969639" lon="121.3188451"/><trkpt lat="24.1969015" lon="121.3189825"/><trkpt lat="24.1969124" lon="121.319054"/><trkpt lat="24.1969419" lon="121.3191408"/><trkpt lat="24.1968984" lon="121.3192736"/><trkpt lat="24.1967088" lon="121.3193055"/><trkpt lat="24.1965351" lon="121.3192947"/><trkpt lat="24.1964317" lon="121.3193739"/><trkpt lat="24.1961702" lon="121.3194777"/><trkpt lat="24.1960605" lon="121.3193886"/><trkpt lat="24.1959528" lon="121.3193162"/><trkpt lat="24.1957938" lon="121.3193994"/><trkpt lat="24.195669" lon="121.3194557"/><trkpt lat="24.1955907" lon="121.3195308"/><trkpt lat="24.1954513" lon="121.3196461"/><trkpt lat="24.1953583" lon="121.3196971"/><trkpt lat="24.1952751" lon="121.3197641"/><trkpt lat="24.1951846" lon="121.3200297"/><trkpt lat="24.1951039" lon="121.3201396"/><trkpt lat="24.1950819" lon="121.3198982"/><trkpt lat="24.1951112" lon="121.3197212"/><trkpt lat="24.1951797" lon="121.3194771"/><trkpt lat="24.1952066" lon="121.3193994"/><trkpt lat="24.1952702" lon="121.3192733"/><trkpt lat="24.1953485" lon="121.319158"/><trkpt lat="24.1953999" lon="121.3189782"/><trkpt lat="24.1954205" lon="121.3188724"/><trkpt lat="24.19545" lon="121.3187822"/><trkpt lat="24.1954481" lon="121.3187041"/><trkpt lat="24.1954586" lon="121.318533"/><trkpt lat="24.1954953" lon="121.3183935"/><trkpt lat="24.1956005" lon="121.318254"/><trkpt lat="24.1956715" lon="121.3181816"/><trkpt lat="24.1957008" lon="121.3180582"/><trkpt lat="24.1958085" lon="121.3179322"/><trkpt lat="24.1959969" lon="121.3178383"/><trkpt lat="24.1960556" lon="121.3177176"/><trkpt lat="24.1960116" lon="121.3174387"/><trkpt lat="24.1960825" lon="121.3171865"/><trkpt lat="24.1960923" lon="121.3170712"/><trkpt lat="24.1960923" lon="121.3168888"/><trkpt lat="24.1961461" lon="121.3166367"/><trkpt lat="24.196222" lon="121.3164757"/><trkpt lat="24.1962954" lon="121.3162585"/><trkpt lat="24.1963253" lon="121.3161015"/><trkpt lat="24.1963422" lon="121.3160695"/><trkpt lat="24.1963459" lon="121.3160246"/><trkpt lat="24.1963326" lon="121.315986"/><trkpt lat="24.1962391" lon="121.3159071"/><trkpt lat="24.1960727" lon="121.3159178"/><trkpt lat="24.1955638" lon="121.3159769"/><trkpt lat="24.1954195" lon="121.3160359"/><trkpt lat="24.1952287" lon="121.3161995"/><trkpt lat="24.1951112" lon="121.3162638"/><trkpt lat="24.1949669" lon="121.3163577"/><trkpt lat="24.1948348" lon="121.3164516"/><trkpt lat="24.1946733" lon="121.3166769"/><trkpt lat="24.1945828" lon="121.3167547"/><trkpt lat="24.1944751" lon="121.3168352"/><trkpt lat="24.1943503" lon="121.3168808"/><trkpt lat="24.194206" lon="121.3168673"/><trkpt lat="24.1940592" lon="121.3168647"/><trkpt lat="24.193905" lon="121.3169022"/><trkpt lat="24.1937411" lon="121.3169639"/><trkpt lat="24.1936698" lon="121.3170575"/><trkpt lat="24.1936033" lon="121.3170993"/><trkpt lat="24.1935401" lon="121.3171473"/><trkpt lat="24.1933717" lon="121.3172429"/><trkpt lat="24.1931172" lon="121.3173636"/><trkpt lat="24.1929215" lon="121.3174226"/><trkpt lat="24.192782" lon="121.3174038"/><trkpt lat="24.1926279" lon="121.3173421"/><trkpt lat="24.1925129" lon="121.3173367"/><trkpt lat="24.1923686" lon="121.3174682"/><trkpt lat="24.1923001" lon="121.3174977"/><trkpt lat="24.1922291" lon="121.3174869"/><trkpt lat="24.1921312" lon="121.317436"/><trkpt lat="24.1920652" lon="121.3171812"/><trkpt lat="24.1920823" lon="121.3169961"/><trkpt lat="24.1921459" lon="121.3168003"/><trkpt lat="24.1922193" lon="121.3166528"/><trkpt lat="24.1923001" lon="121.3165321"/><trkpt lat="24.1922438" lon="121.316355"/><trkpt lat="24.192119" lon="121.316237"/><trkpt lat="24.1920138" lon="121.316229"/><trkpt lat="24.1919247" lon="121.3162792"/><trkpt lat="24.191593" lon="121.3164275"/><trkpt lat="24.191456" lon="121.3164087"/><trkpt lat="24.1913972" lon="121.3163926"/><trkpt lat="24.1913312" lon="121.316347"/><trkpt lat="24.1913116" lon="121.3162692"/><trkpt lat="24.1913043" lon="121.3161485"/><trkpt lat="24.1913186" lon="121.3160339"/><trkpt lat="24.1913237" lon="121.3159447"/><trkpt lat="24.1913219" lon="121.3158515"/><trkpt lat="24.1913746" lon="121.3157851"/><trkpt lat="24.1915307" lon="121.3157205"/><trkpt lat="24.1915979" lon="121.3156604"/><trkpt lat="24.1916492" lon="121.3155557"/><trkpt lat="24.1916346" lon="121.3154055"/><trkpt lat="24.1916076" lon="121.3153102"/><trkpt lat="24.1915517" lon="121.3151937"/><trkpt lat="24.1914193" lon="121.314971"/><trkpt lat="24.1913752" lon="121.3147752"/><trkpt lat="24.1913679" lon="121.3146277"/><trkpt lat="24.191385" lon="121.3144721"/><trkpt lat="24.191454" lon="121.3142808"/><trkpt lat="24.1914739" lon="121.3141805"/><trkpt lat="24.1914571" lon="121.3140918"/><trkpt lat="24.1914082" lon="121.3140008"/><trkpt lat="24.1912785" lon="121.3139676"/><trkpt lat="24.1910278" lon="121.3140081"/><trkpt lat="24.1908565" lon="121.3140644"/><trkpt lat="24.1906804" lon="121.3140591"/><trkpt lat="24.1905157" lon="121.3139954"/><trkpt lat="24.1904406" lon="121.313866"/><trkpt lat="24.1903329" lon="121.3139008"/><trkpt lat="24.1902302" lon="121.3139706"/><trkpt lat="24.1900932" lon="121.3141074"/><trkpt lat="24.1898558" lon="121.3141717"/><trkpt lat="24.1896283" lon="121.3142441"/><trkpt lat="24.1894644" lon="121.3143246"/><trkpt lat="24.1893176" lon="121.3143863"/><trkpt lat="24.1891854" lon="121.3144721"/><trkpt lat="24.1891047" lon="121.3145901"/><trkpt lat="24.1890215" lon="121.3146036"/><trkpt lat="24.1889383" lon="121.3145955"/><trkpt lat="24.1888111" lon="121.3145576"/><trkpt lat="24.1887309" lon="121.3145829"/><trkpt lat="24.1886903" lon="121.3145769"/><trkpt lat="24.1886727" lon="121.3145347"/><trkpt lat="24.1886626" lon="121.3144864"/><trkpt lat="24.1887108" lon="121.3140698"/><trkpt lat="24.1887145" lon="121.3138745"/><trkpt lat="24.1887359" lon="121.3137972"/><trkpt lat="24.1887055" lon="121.3137396"/><trkpt lat="24.1885713" lon="121.3136246"/><trkpt lat="24.1884147" lon="121.3136353"/><trkpt lat="24.1882655" lon="121.3137479"/><trkpt lat="24.1880379" lon="121.3137694"/><trkpt lat="24.1878764" lon="121.3137265"/><trkpt lat="24.1875421" lon="121.3136142"/><trkpt lat="24.1873773" lon="121.3135173"/><trkpt lat="24.1872207" lon="121.3133939"/><trkpt lat="24.1873245" lon="121.3132367"/><trkpt lat="24.1875094" lon="121.3130854"/><trkpt lat="24.1876734" lon="121.3129835"/><trkpt lat="24.1878104" lon="121.3129245"/><trkpt lat="24.1879437" lon="121.3127136"/><trkpt lat="24.1879819" lon="121.312338"/><trkpt lat="24.1881419" lon="121.3119874"/><trkpt lat="24.1881543" lon="121.3118954"/><trkpt lat="24.1881403" lon="121.3117882"/><trkpt lat="24.1880865" lon="121.3116813"/><trkpt lat="24.1880167" lon="121.3116087"/><trkpt lat="24.1878816" lon="121.3115738"/><trkpt lat="24.1877444" lon="121.3115738"/><trkpt lat="24.1875917" lon="121.3115413"/><trkpt lat="24.1875771" lon="121.3115182"/><trkpt lat="24.187561" lon="121.3115058"/><trkpt lat="24.187479" lon="121.3114693"/><trkpt lat="24.1873194" lon="121.3114234"/><trkpt lat="24.1872206" lon="121.3114234"/><trkpt lat="24.1871163" lon="121.3113824"/><trkpt lat="24.1869906" lon="121.3113735"/><trkpt lat="24.1868581" lon="121.3112608"/><trkpt lat="24.1867818" lon="121.3111874"/><trkpt lat="24.1867417" lon="121.3111332"/><trkpt lat="24.1867334" lon="121.3111146"/><trkpt lat="24.1867356" lon="121.3110839"/><trkpt lat="24.1866685" lon="121.3109671"/><trkpt lat="24.1866186" lon="121.3109256"/><trkpt lat="24.1865027" lon="121.3109208"/><trkpt lat="24.1863909" lon="121.3108349"/><trkpt lat="24.1861547" lon="121.3108235"/><trkpt lat="24.1858824" lon="121.310862"/><trkpt lat="24.1855959" lon="121.3107684"/><trkpt lat="24.1853641" lon="121.3106405"/><trkpt lat="24.1849966" lon="121.3104983"/><trkpt lat="24.184979" lon="121.3104032"/><trkpt lat="24.1847649" lon="121.310195"/><trkpt lat="24.1845991" lon="121.3101661"/><trkpt lat="24.1845387" lon="121.3101264"/><trkpt lat="24.1843946" lon="121.3100917"/><trkpt lat="24.1842938" lon="121.3099675"/><trkpt lat="24.1841531" lon="121.3098609"/><trkpt lat="24.184096" lon="121.309761"/><trkpt lat="24.1840126" lon="121.3096852"/><trkpt lat="24.1839755" lon="121.3095689"/><trkpt lat="24.1839694" lon="121.3095496"/><trkpt lat="24.183841" lon="121.3093546"/><trkpt lat="24.1837729" lon="121.3092884"/><trkpt lat="24.1837449" lon="121.3092848"/><trkpt lat="24.1836817" lon="121.3092439"/><trkpt lat="24.1836624" lon="121.3091816"/><trkpt lat="24.1836251" lon="121.3091169"/><trkpt lat="24.1835917" lon="121.309025"/><trkpt lat="24.1835948" lon="121.3089969"/><trkpt lat="24.1836173" lon="121.3089696"/><trkpt lat="24.183622" lon="121.3089398"/><trkpt lat="24.1835617" lon="121.3088568"/><trkpt lat="24.1834419" lon="121.3088291"/><trkpt lat="24.1832079" lon="121.3088849"/></trkseg></trk></gpx>'''
    
    print(f"\n處理用戶提供的GPX資料:")
    coordinates_from_string = extract_trkpt_from_gpx_string(user_gpx_content)
    
    if coordinates_from_string:
        save_coordinates_to_json(coordinates_from_string, "/workspace/user_gpx_coordinates.json")
        print(f"從用戶GPX資料提取了 {len(coordinates_from_string)} 個座標點")
        
        # 顯示前5個座標點作為範例
        print("\n前5個座標點範例:")
        for i, coord in enumerate(coordinates_from_string[:5]):
            print(f"  {i+1}. {coord}")

if __name__ == "__main__":
    main()