

## Method 1 - reload image
1. onframechange: Switch the source of an image-datablock.

**Result**  
- Slow. - Cache is *not* used. The image is reloaded.
- Beim ersetzen von bpy.types.image.filepath wird das Bild neu geladen.  
  Fehlende Bilddateien in einer Sequenz werden als pink dargestellt



## Method 2 - switch images

1. Create an image-datablock for images one the hard drive.
2. onframechange: Switch the image-datablock of an *image texture* node in a material.

**Result**  
- Fast - Cache is used.



## Method 3 - frame driver on image datablock

1. Create an image sequence with a keyed/driven offset.
    - load rgba sequence
    - set offset to expression `2 - frame`

**Result**  
- Fast - Cache is used.
- Broken.
    - scrubbing in solid view ignoriert “offset”
    - texture paint wird nicht gespeichert
