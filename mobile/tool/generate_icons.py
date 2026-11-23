#!/usr/bin/env python3
"""Generate original Library Smart app icon for Android and iOS; no third-party assets.

Run after "flutter create" so the platform projects exist.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]

def icon(size):
    scale = 4
    n = 1024 * scale
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Blue-to-indigo premium background, slight cool highlights.
    for y in range(n):
        t = y / n
        color = (int(15 + 25 * t), int(36 + 7 * t), int(93 + 71 * t), 255)
        d.line([(0, y), (n, y)], fill=color)
    circle = (0.075*n, 0.075*n, .925*n, .925*n)
    glow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((.48*n,-.26*n,1.24*n,.50*n), fill=(76, 210, 213, 55))
    glow = glow.filter(ImageFilter.GaussianBlur(0.17*n))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    def poly(coords, color):
        d.polygon([(int(x*n), int(y*n)) for x,y in coords], fill=color)
    def line(points, color, width, joint="curve"):
        d.line([(int(x*n),int(y*n)) for x,y in points],fill=color,width=int(width*n),joint=joint)
    # Book cover shadow, two open pages, rounded spine.
    poly([(.18,.35),(.48,.39),(.5,.77),(.20,.72)],(8,23,64,115))
    poly([(.52,.39),(.82,.35),(.80,.72),(.5,.77)],(8,23,64,115))
    poly([(.16,.31),(.47,.35),(.49,.71),(.19,.67)],(244,249,255,255))
    poly([(.53,.35),(.84,.31),(.81,.67),(.51,.71)],(222,242,251,255))
    poly([(.22,.39),(.43,.42),(.44,.62),(.23,.59)],(219,231,250,255))
    poly([(.56,.42),(.78,.39),(.77,.59),(.56,.62)],(190,221,252,255))
    line([(.50,.38),(.50,.73)],(34,211,200,255),.035)
    line([(.22,.69),(.48,.75),(.50,.77),(.52,.75),(.78,.69)],(74,217,204,255),.025)
    # Spark of learning.
    d.ellipse((int(.67*n),int(.18*n),int(.77*n),int(.28*n)),fill=(91,239,211,255))
    d.ellipse((int(.78*n),int(.29*n),int(.825*n),int(.335*n)),fill=(188,251,237,255))
    return img.resize((size,size), Image.Resampling.LANCZOS).convert("RGBA")

densities = {"mdpi":48,"hdpi":72,"xhdpi":96,"xxhdpi":144,"xxxhdpi":192}
res = ROOT / "android" / "app" / "src" / "main" / "res"
for density, px in densities.items():
    out = res / f"mipmap-{density}" / "ic_launcher.png"
    out.parent.mkdir(parents=True,exist_ok=True)
    icon(px).save(out)
# Explicitly include a 1024px marketing icon and all required iOS sizes.
appicon = ROOT / "ios" / "Runner" / "Assets.xcassets" / "AppIcon.appiconset"
appicon.mkdir(parents=True,exist_ok=True)
entries = []
specs = [("iphone",20,[2,3]),("iphone",29,[2,3]),("iphone",40,[2,3]),
         ("iphone",60,[2,3]),("ipad",20,[1,2]),("ipad",29,[1,2]),
         ("ipad",40,[1,2]),("ipad",76,[1,2]),("ipad",83.5,[2]),
         ("ios-marketing",1024,[1])]
for idiom,points,scales in specs:
    for factor in scales:
        pixels = int(points*factor)
        name = f"ls_{idiom}_{str(points).replace('.','_')}x{factor}.png"
        icon(pixels).save(appicon / name)
        entries.append({"size":f"{points}x{points}","idiom":idiom,
                        "filename":name,"scale":f"{factor}x"})
import json
(appicon/"Contents.json").write_text(json.dumps({"images":entries,
    "info":{"version":1,"author":"xcode"}},indent=2)+"\n",encoding="utf-8")
print("PASS: Generated Library Smart launcher artwork for Android and iOS.")
