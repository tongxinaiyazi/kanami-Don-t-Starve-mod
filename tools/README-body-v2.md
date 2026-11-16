# Body-v2 candidate compiler

Run with `py -3 tools/build_kanami_body_v2.py`. Default inputs are
`art/klbq_kanami/body-v2/registration.json` and `native-contract.json`.
Default output is `D:/SOFTWARE/CodexData/temp/kanami_body_v2_candidate`.
No production files, installed mods, original artwork, or fixed upload directory
are written. `--actions-only` compiles actions before artwork is available;
`--validate-only` checks registration without calling Klei's compiler.

Registration format:

```json
{
  "frames": {
    "leg/0": {
      "image": "sprites/leg_0.png",
      "canvas": [40, 80],
      "centre": [-4.5, 23.0],
      "duration": 1,
      "semantic": "Native leg frame 0: author-reviewed pose description",
      "original": true
    }
  }
}
```

Every native frame must have an entry. PNG canvas dimensions and local centre
are copied verbatim into build.xml. The build writer preserves authored pixels
and centres. Centre is the native build x/y convention, not a top-left
position or normalized Spriter pivot. Width/height are the full PNG canvas.
Duration must match the native contract. Each entry needs a non-empty semantic
description and explicit original-art declaration; these record author review,
and cannot automatically prove visual pose correctness or ownership.

An intentionally hidden non-body layer can use a transparent PNG only with
`intentional_empty: true` and a non-empty `reason`. Main body, limbs, head and neck
cannot be replaced with blank images. The optional `arm_upper_skin` overlay
may also be transparent when the complete clothed arm is drawn in `arm_upper`:
declare `intentional_empty: true`, an explanatory `reason`, and
`covered_by: "arm_upper"`. At least one main arm entry must exist and all
registered `arm_upper` frames must remain non-empty. This exception avoids
drawing the same arm twice; it does not allow blank main limbs or other body
symbols. Verify the layering visually across native poses.
Exact duplicate images within one symbol
require `shared_pose_reason`, explaining why these frame numbers actually share
a pose. Do not use this exception to skip bent limbs, different grip poses,
expressions, or special action frames. New symbols can be added explicitly.

Ordinary idle, run, careful/groggy walk, food, feast, attacks, pickup, hit and
axe/pickaxe/shovel aliases retain native frame identity, angular motion,
timing and events. `retarget_kanami_body.py` exports connected joint chains.
Upper arms use a fixed length of 26, forearms 21, leg paths 38 and ankle-to-toe
axes 14. The projected upper-arm slot uses 11. Hands have a uniform bounded size.
Torso length uses 0.94 and transverse width 1.15 of its authored basis.
These authored physical dimensions remove native sleeve stretch and shear that
made the replacement's bare limbs grow during movement and work.
The bent leg/6 knee is registered at (-15, 11). Its constant 38-unit limb path
keeps at least 30 units of hip-to-ankle span during work, avoiding a folded
stocking disappearing beneath the skirt.
Normal and carrying arms are resolved separately. Native food uses normal arms;
work projections show the tool while retaining the normal working arm track.
Food aliases omit the weapon track because inventory food use may be
server-driven while the owning client state graph stays idle.
Weapons and props follow their physical hand's local grip offset. Pelvis waist
is the root of the torso chain. Both waist endpoints are bound and hips follow
the adjusted skirt. Nine local opacity samples check the complete garment seam.
Exact sole-outline support retains the original native
ground and jump trajectory after resizing the limbs. Foot support metadata
contains coordinates only, with no native pixels in the runtime or source pack.
The authored head neck-base follows the torso collar. Hair and facial layers
move with the same head displacement. Deep-bend torso/9 has explicit shoulder
points independent of its crescent contour controls. Pelvis/9 uses the native
right-facing waist opening. All live pelvis sprites contain clothing only.
Facial translations attach the authored eye landmark
to the head's face opening. This is required because native facial excursions
can move the eyes into the fringe of the shorter anime face. Expression frame
identity remains native. The face basis follows a fixed neutral head-relative
transform so expressions keep their authored proportions. Eye and mouth art
have independent registration. Eye sources use their measured iris centres.
The final transparent row gap separates lips from eyes so speaking frames do
not leave a duplicate upper lip in the eye layer. Neutral mouths use an extremely
small, thin closed line, around 3 units wide. Open expressions remain visible
and are bounded to 7 by 5. The profile eye uses scale 0.15 and head-local centre
(20, -45).
Native talk uses dial_loop and refusal uses refuseeat, both with facing 255.
Their aliases retain native frame identities, timing, audio and state events.
Winter's Feast uses the same attachment and
preserves its native server/client animation queues.
Special shooting, crossbow, string, cast and revive names remain available.
Held weapons retain their shooting orientation/recoil adjustment. Retargeting
retains the authored angular animation while fixing limb size and connections.
Long hair is authored for native hair layers. Front and profile rear-hair tracks
are behind both arm variants to keep the carrying palm visible. The front
curtain has a continuous centre, aligned beneath the skull. The back curtain
retains its coverage. Joint opacity checks use adjacent body parts only.

Run `check_kanami_joint_poses.py --exported <candidate build folder>
--action-zip <candidate action zip> --all-actions` for compiled readback. This checks explicit
joint landmarks and local alpha regions for neck, shoulder, elbow, wrist, waist, hip
and ankle. Only adjacent parts contribute pixels. Hair and unrelated overlap
cannot make a disconnected joint pass. Deliberately displaced-part regressions
verify that the gate rejects shoulder, hip, waist and ankle failures.

Tests: `py -3 tools/test_build_kanami_body_v2.py`. These check canvas/pivot
preservation, missing/blank/repeated poses, duration drift and current installed
native pose identity, fixed limb dimensions, sole contact and hand-local grip
offsets. Visual acceptance and gameplay tests are separate steps.

The current contract contains 132 original build frames. Animation references
also include engine equipment layers, effects, beard and character-specific
optional layers that Wilson's build does not provide. Those must not be filled
with copied reference pixels. Coverage of all 132 native frames is required,
including frames unused by the small ordinary-animation audit subset.

## Candidate-only full-cycle previews

```powershell
py -3 tools/render_kanami_body_v2.py --art art/klbq_kanami/body-v2
py -3 tools/render_kanami_body_v2.py --exported D:/SOFTWARE/CodexData/temp/kanami_body_v2_candidate/exported/klbq_kanami --weapon-exported art/klbq_kanami/exported/swap_klbq_finale
py -3 tools/render_kanami_body_v2.py --exported D:/SOFTWARE/CodexData/temp/kanami_body_v2_candidate/exported/klbq_kanami --action-zip D:/SOFTWARE/CodexData/temp/kanami_body_v2_candidate/compiled/anim/klbq_kanami_actions.zip
```

Default output: `D:/SOFTWARE/CodexData/temp/kanami_body_v2_preview`.
The six actions are `idle_loop`, `run_loop`, `eat`, `chop_loop`,
`pickaxe_loop`, `shovel_loop`. Each actual native direction gets a complete
cycle GIF and a 12-frame contact sheet, in both empty/carry poses and with
hair shown/hidden. Use `--actions idle_loop run_loop`, `--mode empty`,
`--hair hide`, `--samples 24`, `--scale 1.35`, or `--size 440 480` to focus QA.
Use `--action-zip` to inspect the actual compiled character clips with attached
expressions. Without it, the renderer displays the unretargeted native reference.
Winter's Feast pre/loop/post clips can be selected explicitly. Connection audits
retain raw silhouette alerts and separately record whether the gap is covered
by the character's hair/body. A covered alert is not an anatomical-overlap pass.
The current native eat action has only facing 255, so its output is labelled
`nofaced`; the tool does not invent three direction variants.

The renderer reads only the selected candidate source, never falls back to an
old character export. Build frame durations expand to every covered frame index.
Symbol lookup is case insensitive, matching native symbol hashes. The explicit
optional weapon source must contain only swap_object; it cannot overwrite body
images. Without a weapon source, carry mode displays the carrying arm pose and
reports the missing swap_object frame. Missing visible symbols are listed in
`render-report.json`; optional equipment/FX/hair-layer absences require review
and are not silently called visual success. The report identifies the source and
metadata hash. GIF timing uses rounded centiseconds to preserve the overall
native frame rate. Every animation frame is rendered; contacts alone are sampled.

`py -3 tools/test_render_kanami_body_v2.py` verifies candidate-specific pixel
content at its off-centre native origin, duration ranges, case-insensitive
symbols, carry/empty/hair filters, full GIF frame count and timing. These are
pipeline tests using deliberately synthetic fixtures, not replacement artwork
or a claim that the candidate character has passed visual/game acceptance.
