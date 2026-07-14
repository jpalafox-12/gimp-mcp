#Requires -Version 5.1
<#
.SYNOPSIS
  Layer cutout demo: color + matte + defringe → clean PNG (no soft glow).
.EXAMPLE
  .\logo_cutout_layers.ps1
  .\logo_cutout_layers.ps1 -Src C:\path\logo.png -OutDir C:\Users\me\Downloads
#>
param(
    [string]$Src = "$env:USERPROFILE\Downloads\Logo-luxury-original.png",
    [string]$OutDir = "$env:USERPROFILE\Downloads\logo-layers-debug",
    [int]$KeepBottom = 712,
    [double]$Thr = 34
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

python -c @"
from pathlib import Path
from PIL import Image
from gimp_mcp.layers import cutout_layers, export_layer_debug
import numpy as np

src = Path(r'$Src')
out = Path(r'$OutDir')
out.mkdir(parents=True, exist_ok=True)
raw = Image.open(src).convert('RGBA')
im = raw.crop((0, 0, raw.width, min($KeepBottom, raw.height)))
res = cutout_layers(
    im, mode='gold', thr=$Thr, soft=4, hard=True, hard_thr=70,
    dilate=1, erode=0, defringe_on=True, aa=0.0, unpremult=True,
)
paths = export_layer_debug(res, out / 'layer')
# also save white/dark preview
rgba = res['rgba']
for bg, tag in [((255,255,255),'white'), ((10,10,12),'dark')]:
    c = Image.new('RGB', rgba.size, bg)
    c.paste(rgba, mask=rgba.split()[-1])
    c.save(out / f'preview_{tag}.png')
a = np.array(rgba)
al, pres = a[:,:,3], a[:,:,0:3].max(2)
partial = int(((al>5)&(al<220)).sum())
bright = int(((al>5)&(al<220)&(pres>140)).sum())
print({'layers': paths, 'partial_alpha_px': partial, 'bright_fringe_px': bright, 'size': rgba.size})
"@

Write-Host "Layers written to $OutDir" -ForegroundColor Green
explorer $OutDir
