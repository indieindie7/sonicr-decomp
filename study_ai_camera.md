# Sonic R (Saturn): AI racers, race logic, camera

Source: Ghidra dump ghidra/decomp_0.c (binary cd/0.BIN, base 0x06004000) and the disc files. Everything below is read from code or bytes unless marked GUESS. Angles use a 4096-unit circle. World positions are 12-bit fractions (<<12). Racer progress is a waypoint index <<21.

## 1. AI path format
Each course has an AISTUFFn.BIN (e.g. cd/BEACH/AISTUFF1.BIN). It is NOT RNC packed (22304 bytes for Beach 1). race_SetupCourse (line 39292 of the dump) copies four blocks into LWRAM:
- 0x0000: gates, 16 bytes each, big-endian 8 shorts: x0, z0, x1, z1, y, three spare (zero in Beach). A gate is a line across the track: (x0,z0) is one edge, (x1,z1) the other. Beach gate 0 is 422 units wide, neighbours about 294 units apart.
- 0x4000: section table, 8-byte entries {count, start} as two big-endian ints, ended by -1. Beach: (203,0) (37,203) (81,240) (32,321) (36,353) (28,389) (14,417) (15,431) (14,446) (7,460) (9,467); 476 gates in total. Section 0 is the main loop, the rest are branches or shortcuts.
- 0x4200 (LWRAM 0x00244200, global 0x0603c114): grid A, 0xE00 bytes of per-gate action strips. ai_UpdateRacerBehaviour (line ~171 of its decomp) reads gridA[gate.word0 + racer lane offset] while the racer's path flag is 1, where gate.word0 is the short at +0 of the current 16-byte gate record. Same action-byte format as grid B.
- 0x5000: "grid B", 32x32 bytes of action codes (high nibble = action, low nibble = parameter). On Beach 1 only a few cells are used: action 1 (10 cells), 2 (3), 4 (6), 5 (19), rest 0. Grid B (LWRAM 0x00245000, global 0x0603c058) is used when the path flag is not 1, indexed by the world cell (x, z divided by the cell size, row*32+col). Action byte, as read in ai_UpdateRacerBehaviour: high nibble 0 = jump/hop: low 2 bits pick a jump-strength table (1, 2, 3), bit 2 must match a racer state flag, bit 3 = conditional (only when the cell changed and a random byte < 0x21, about 13%). The same nonzero cell on consecutive frames makes the racer weave (a steer offset swings by 8 between limits); a new cell resets it to a random +/-1. (Fine meaning of the higher nibbles is still a GUESS.)
- 0x5400 (LWRAM 0x00245400, global 0x0603bf70): branch table, decoded in ai_AdvanceSegmentQueue 0x06034384. 160 entries = 10 branch points x 16 character slots, 5 bytes each; index = (branch-1)*16 + racer character (+0x234). A gate record's +0xa is the branch-point id (n>0 -> n-1, n<0 -> ~n), +0xc the target section (same encoding) and +0xe low byte the start gate in it; at a branch gate the racer rolls 0..99 from a random byte table (0x0600bd74):
  - b0 = take chance when ahead of the reference racer (progress word +0x4c >> 21 compared to 0x0600b3f8-relative leader), raised by diff*16/K when > 50;
  - b1 = take chance when behind (lowered when > 50); difficulty byte forces it to 0 or 10 for slow racers (+0x5c below a threshold);
  - b2 / b3 = chances inside the band (taken if the roll is below either);
  - b4 = gate condition: 1..0x3f = record (b4-1) in a 12-byte table (+8 open flag, +0xa required count vs racer +0x18, e.g. ring doors); 0x40 / 0x41 = two global flags; 0 = none. A closed condition means no branch.
  Mode 2 or 3 (time attack style) disables branching. For Scorcher: per-character, per-branch take chances plus a position-dependent push is a cheap way to make AI racers take shortcuts differently.
PATH/PATH1-4.BIN (2280 to 19384 bytes, unpacked) are NOT AI paths: they are attract-demo pad recordings (one 16-bit pad word per frame, e.g. 0x0100 / 0x4100), loaded by demo_LoadAttractRecording (0x0602cc8c, was ai_LoadPathFile) into the replay buffer 0x002e8000 that replay_RecordPad* writes. (Corrected 10-13.)
Check script: scratchpad chk.py (decodes the section table and gates; its output matches the numbers above).

## 2. How an AI racer picks a target and steers (ai_UpdateRacerBehaviour 0x06033480)
Runs every frame per CPU racer; skipped while the racer is in a special mode (+0x1b0 nonzero).
1. A random value comes from a sine table indexed by a per-racer counter. An "aggression" value (+0x1b8) drifts by 1 per frame towards a goal (+0x1bc, centred on 0x7f).
2. If another racer in the same section is 1..4 gates ahead, the goal is set to 0x80 plus a random value so the racer takes a different lane for a while (shared countdown from 8).
3. A lateral fraction (+0x1c2) is kept between 0x40 and 0xc0 (of 0x100) across the gate. The target point is a blend of the gate's two edges, not a fixed racing line.
4. Near the target (within 0x7ff squared units), flags in the gate (masks 0x100, 0x200, 0x400, 0x700) pick an aggression table per character slot (+0xea). So gate flags carry "go wide / go tight" hints (GUESS on the exact meaning).
5. World x,z mapped into the 32x32 grid B gives an action byte, acted on only when the cell changes. High nibble: 0 = lane or trick change (bit 8 means a random roll ~25%), 1/2/3/6/7/f = set a steering heading (low nibble << 8, a 16-direction compass, mirrored for the other lane side), 4/5 = jump to section N and remember the position, 8-e = set a speed value (low 7 bits x 2), re-apply stats, reset the queue and look-ahead budget (+0x110 = 200).
6. Steering turns toward the target at a limited rate (+0x1a0 clamp, +0x114 accel). Exact angle-error-to-input mapping not read (GUESS: proportional with clamp).

## 3. Segment queue (ai_AdvanceSegmentQueue 0x06034384, ai_PopSegmentQueue 0x060348a8)
The racer looks ahead using a distance budget (+0x110). The queue is a ring of 16 runs, each (section, start gate, length), head and tail at +0x148 and +0x14c. Each call adds gates while the budget lasts; at section ends it continues or takes a branch from the branch table by a random roll weighted by rubber band state (GUESS on weights). Pop drops the head run once passed. The steering target is the gate at the front of the queue.

## 4. Avoiding other racers
ai_AvoidNearbyRacers (0x060289c0) does NOT steer. It tests contact between racers; on contact it spawns scattered rings and subtracts 10 from a counter (rename proposed: racer_CheckContactRingScatter). Avoidance is the lane choice in step 2 above: a racer 1..4 gates behind another picks a different lane for a timed period. No collision steering.

## 5. Rubber banding and speed caps
- ai_SelectSpeedCap (0x06035c34): base cap B (16-bit at 0x0603bf40) from n = 2*level+1 (5 on the last level or in battle mode; +1 when a 0x7f setting is on). Table: n=1 0x38, 2 0x48, 3 0x50, 4 0x68, 5 0x80, 6 0xa0, 7 0xc0, otherwise 0x28. Then minus (character/level table value * (n+1) / 32), x3/4 when one flag is set, halved in two-player mode, reduced by 1/4 on one specific course (non-2nd place). Clamped to 0x20..0xc8.
- ai_UpdateRubberBand (0x06035974): diff = rival progress minus player progress, in waypoints (>>21). Rival = the racer in place 1 (or 2 if the player leads). T = threshold at 0x0603bf94 (set at runtime; value not found). Current cap (0x0603bfa0) from base B:
  - RESOLVED (by hand): T is set per course by race_SetupCourse 0x06033228 (switch on the course number; the store goes through the pool pointer at 0x0603343c): course 1 = 0x4e (78), course 2 = 0x66 (102), courses 3 and 4 = 0xc8 (200, the 16-bit constant at 0x060333da), course 5 = 0x31 (49) waypoints. The same switch sets three more per-course values (-3/-4/-2, 3/4/2, 10/12/5, 0x50/0x60/0x20) that look like AI tuning (guess).
  - diff > T/2 (CPU well ahead): B/2 (min 0x20).
  - T/4 < diff <= T/2: B*7/8.
  - diff < -T (CPU far behind): B*5/4 (max 0xc8).
  - diff < -T/2: B*3/2 (max 0xc8).
  - diff > 2*(0x0603c520) (nearly level again): B.
  - else the cap is left unchanged (hysteresis). Steps snap; no smoothing.
- The same function also steps a ghost/replay object (counter at +0x150 against 0x3c0 minus a stat); not studied.

## 6. Race position and laps
- race_UpdateProgressAndPlaces (0x06029358): progress = (lap-adjusted waypoint index) << 21 plus a sub-node distance term (path_ProjectOntoSegment). Places come from sorting the five racers by progress, stored at +0x5c.
- race_UpdateLapCrossing (0x060296a0): a 3-bit sector code relative to the start line; a lap counts only when sectors are passed in order, so reversing over the line gives nothing. Wrong-way flag at +0x60, lap at +0x5e.
- car_AlignToTrackSegment (0x0602ed64) tilts the car to the track slope; path_InterpolatePosition (0x0602ea40) and path_ProjectOntoSegment (0x0602ec38) place the car on a segment.

## 7. item_UpdateHomingProjectiles (0x06028da8)
Despite the name this is not a homing missile. Four slots (12 bytes each) with timers. Each slot springs a point toward a target (accel 0x80 per frame, halved on overshoot), draws a sparkle sprite each frame (ring buffer of 0x3c sprites), and when within sqrt(0x2fff) of the target it applies a velocity to that racer and frees the slot. Looks like a collected ring or item flying to the player. GUESS name: fx_UpdateCollectFlyToRacer. Not renamed (too uncertain).

## 8. Camera
cam_UpdateFollowSmooth (0x06019038) is the in-race camera; cam_UpdateFollowSimple (0x06019548) is the same offset without smoothing.
- Aim point: car position moved backwards along the car heading by 0x380 (896 units), or 0x4b0 (1200) when the character slot is 4; height = max(ground height under that point, car height) + 0x70. A flag lowers it by 0x30. While a countdown at 0x600bd68 is above 0x1f (GUESS: start sequence) the offset is blended with a per-start-slot camera table (0x600cc08, 12-byte entries).
- Smoothing: camera position (stored <<4) moves by (pos - target)/divisor each frame; divisor = zoomSpeed>>2 for x and z, zoomSpeed>>1 for y. Normal zoomSpeed 0x12: x,z lag about 1/4 per frame, y about 1/9. With the flag at +0x9c set, zoomSpeed 0x40: 1/16 and 1/32 (loose).
- cam_EaseZoomSpeed (0x06018fe4): zoomSpeed moves 2 per frame toward 0x12, or snaps to 0x40 when the +0x9c flag is set, then eases back.
- cam_CalcLookAtAngles (0x06018ed0): yaw = atan2 + 0x800; pitch = -atan2(horizontal distance, height difference), aiming 0x28 above the target. The smooth camera moves its angles only 1/4 of the difference per frame (wrapped to signed 12 bit).
- Look-ahead: none. The camera sits behind the car heading, not velocity. It also queries the nearest gate (ai_NearestWaypointXYZ) for its own use (GUESS: visibility).
- cam_UpdateTrackViewpoints (0x06019760): replay/broadcast camera. 0x78-frame shot timer (2 s at 60 Hz); a table at 0x06038380 gives mode and angle per shot. Mode 0 = fixed trackside viewpoint nearest the car (rechecked at 0x5a, 0x3c, 0x1e remaining), 1 = behind the car at 1100 units, 2 = behind with a rotating angle (+0x20 per frame), 3 = in front at 1100 units with ground clamp and a vertical kick. Position eases 1/3 per frame (x,z) and 1/4 (y).
- cam_InitFromTarget (0x06019e90): copies car position (<<4) and angles into the camera, zeroes the zoom-speed field.

## For Scorcher:
1. Use gate lines (left and right point per gate) as the AI path, not one spline: each AI keeps a lateral fraction between 0.25 and 0.75 of the gate and changes it slowly with noise. Cheap, lively, gives overtaking room.
2. A look-ahead distance budget with a queue of path runs makes branches and shortcuts just extra sections with a roll.
3. Make lane choice the whole avoidance: a racer a few gates behind another shifts lane on a short timer. No collision steering needed.
4. Paint behaviour into a 32x32 action grid over the map (byte = type + parameter: boost, go wide, jump to section, set speed). AI reads it only when the cell changes.
5. Rubber band by stepping the speed cap in bands from the progress difference with hysteresis (1/2, 7/8, 1, 3/2 or 5/4 of base), with a floor and ceiling and a per-difficulty base table. Never apply it to the player.
6. Progress = waypoint index plus sub-node distance as one number for sorting places; count a lap only when sectors are passed in order.
7. Chase camera: behind the heading at a fixed distance, a fixed lift above ground, lag x,z about 1/4 per frame and y about 1/9, aim slightly above the car, ease angles by 1/4. Loosen to 1/16 on a hit or trick.
8. Cheap broadcast cameras for replays and finish: a 2 second shot timer over four modes (trackside, behind, orbiting, in front) from a table.
9. Ease the lag factor in constant steps (2 per frame) rather than snapping, to avoid camera popping on mode change.
10. GUESS: the spring toward a target (accel constant, halve on overshoot) is a good cheap pickup fly-to-player animation.
