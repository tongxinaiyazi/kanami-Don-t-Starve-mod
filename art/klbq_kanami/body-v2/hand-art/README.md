# Original hand registration

`register_hands.py` mechanically crops the 6-column original hand sheet and
registers hand/0 through hand/19. It writes only `sprites/hand_N.png` and
`registration-hands.json`. It does not draw, recolour, trace, or copy game pixels.

Each POSES entry contains the reviewed atlas wrist-entry point, an explicit
scale, clockwise rotation, and optionally a native wrist coordinate. The native
local origin is preserved in the new padded canvas. No bounding-box centering
or automatic fit is used. Wrist points are selected within the cuff entrance,
leaving several visible pixels of overlap for the forearm. The source wrist
accessory stays in the original art; no second sleeve or forearm is drawn.

Most native hands use a wrist origin. Hand/18 and hand/19 instead have palm
origins, so their source wrist is mapped to a separate local wrist coordinate.
Hand/15 is the cup prop, anchored at its rim. Alternate slots 11, 12, 16 and 17
retain independently drawn gloved poses. Every pose uses its own source cell.

An alpha >= 24 mask locates the source crop; a 3-pixel crop margin preserves
antialiasing. Actual RGBA pixels, including their original alpha, are transformed
with bicubic resampling. No threshold mask is written over the artwork.

Rebuild with:

```powershell
& 'D:/SOFTWARE/CodexData/runtimes/codex-primary-runtime/dependencies/python/python.exe' art/klbq_kanami/body-v2/hand-art/register_hands.py
& 'D:/SOFTWARE/CodexData/runtimes/codex-primary-runtime/dependencies/python/python.exe' art/klbq_kanami/body-v2/hand-art/qa_hands.py
```

QA mixes the original hand cutouts and new upper-body registration with native
reference pixels solely in D:/SOFTWARE/CodexData/temp/kanami_body_v2_hands. Those
mixed pictures are local references, never distributable character resources.
The renderer uses unmodified native idle/run/eat/chop/pickaxe/shovel matrices in
both empty/carry modes. Eat is native facing 255. Every cycle is rendered; the
combined contact samples idle/run/eat. No weapon is included in this hand joint
QA. Weapon alignment and final character appearance still require integrated
candidate and in-game checks.
