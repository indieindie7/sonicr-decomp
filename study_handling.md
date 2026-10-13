# Sonic R (Saturn) handling study

Source: Ghidra dump ghidra/decomp_0.c (program cd/0.BIN, base 0x06004000, SH-2 big-endian). Only hand-named functions were read. "GUESS" marks anything not directly confirmed. Many constants are literal-pool values (DAT_/PTR_ names) read from 0.BIN at (addr - 0x06004000).

## Formats
- World positions: 12-bit fraction (value << 12 = section units). Track vertices are shorts multiplied by 0x1000.
- Angles: 0..0xfff is a full circle (0x1000 = 360 deg). Headings are masked with 0xfff. Atan2 result is >>4.
- Sin/cos tables: 14-bit shorts, used with >>2 to give 12-bit results. 2D dot products via math_DotProduct2DFixed.
- Car struct offsets seen: +0x42 timer, +0x4c track progress (>>21 gives a coarse position index), +0x5c/+0x5e state words, +0x6e drift flag (-1/0/+1), +0xea character id (DAT_0602d3ec = 234).

## Per-frame update order
Function race_UpdateCarsAndCollisions (0601f5c0), only when the pause/countdown value is 0:
1. Human pad(s) go through replay_RecordPad* (0601f31c, 0601f3f0, 0601f4dc) -> car_UpdatePhysics (0602d2a0) earlier in the frame. Pad words are recorded or replayed there (end marker -1), so a replay is a stream of pad words.
2. car_CollideCarsSwept (06034b40) for all 10 pairs.
3. car_CollideCars (0602e32c) for all 10 pairs.
4. 2-player waypoint refresh, then ai_UpdateRubberBand (06035974).
5. For racers 1..4 (non-player cars): ai_UpdateRacerBehaviour, car_UpdateMovement (06034f5c), car_UpdateCollisions (06030dbc).
Player cars also run car_UpdateCollisions after car_UpdatePhysics.

car_UpdateCollisions order: trigger proximity, wall resolve (car_ResolveWallCollision 060308e0), ground collision (car_UpdateGroundCollision 0602fd84), ground contact check (car_CheckGroundContact 060300ec), clamp the move, reset vertical velocity on contact, body tilt (car_UpdateBodyTilt 0602df7c). Airborne branch: car_UpdateVerticalBounce (0602fa1c) plus track_GetLowestGroundHeightAt (06030334). Finally decrement the +0x42 timer.

## Input to motion (car_UpdatePhysics 0602d2a0)
- Pad bits: 0xe/0xf steer left/right; 0x40 and 0x10 cancel/boost-type buttons; bit 8 and bit 0xd charge or jump (GUESS on exact button mapping).
- Steering adds/subtracts a per-character steer rate (table field [2]) to the heading each frame; heading wrapped with &0xfff. Digital pad bits only (no analog axis read). Steer rates range 25 to 45.
- Velocity is kept as forward and lateral components in the car frame; each frame both are clamped, then rotated to world with the sin/cos table.
- Drift: flag +0x6e is set to +1/-1 when lateral and forward speeds cross thresholds (steering hard at speed), cleared when they drop. Lateral speed decays by the friction field [4], so low friction (0 to 512) means long slides, high (2048) grippy (GUESS on direction).
- Each character then runs a special-case state machine (modes 0..9 keyed on character id) for abilities. Details not decoded.

## Character table (0603aee8)
10 rows (characters 0..9), 10 ints each, stride 0x28. Values as in 0.BIN:
```
0: 0x33000 3584 35 4608 1024 49 0       0x36000 98304 0x24000
1: 0x2d000 4096 45 2048  512 56 0x24000 0x30000 98304 0x1b000
2: 0x33000 4608 35 3584 2048 56 0x30000 0x30000 98304 0x1e000
3: 0x24000 5120 35 3584 2560  0 0x36000 0       0     0x21000
4: 0x2a000 3584 40 3072  512  0 0       0       0     0x2a000
5: 0x36000 4096 35 2560 1536 70 0       0       0x1e000 0
6: 0x2d000 3072 25 4096    0  0 0       0       0     0x24000
7: 0x36000 5120 30 4096 1536 70 0x33000 0       0x1b000 0
8: 0x2d000 5120 35 4608 1536  0 0       0       98304  0
9: 0x3c000 5120 40 4608  512 56 0       0x3c000 98304 0x2a000
```
Column use (partly GUESS): [0] top speed / accel base (12-bit fixed, 0x33000 = 51.0 units); [1] acceleration (x3/2 used); [2] steer rate; [3] drag; [4] friction/grip; [5] small per-character value; [6] boost speed; [7] jump launch scale; [8] second speed cap; [9] extra special value. Row 9 has the highest [0] (0x3c000), row 3 the lowest (0x24000).
car_InitFromCharacterStats (06032d90) copies a subset into the car: [0]*0x24>>5, [1], [2]*3/2, [4]/2, [3]<<2, plus one short from a byte table by x9 (2P) or x7, >>3.

## Rival motion (car_UpdateMovement 06034f5c)
Not pad-driven: gravity is added to vy (pool value DAT_06035190, clamp DAT_060351a0 read as 0x25800; RESOLVED: the literal is a 16-bit mov.w constant 0x3000 = 3.0 units per frame in 12-bit fixed, terminal fall speed 0x25800 = 37.5), heading steers toward the next waypoint via Atan2 with a capped per-frame turn step, throttle follows a small state machine, and if a mode flag is set it defers to car_UpdateVelocityTrackHeading (0602e778) which follows the section heading (+0x14). car_UpdateVelocityGround (0602e5d8) handles the grounded velocity update.

## Ground following
- Track = 32x32 grid of cells; each cell lists section ids. track_FindSectionContainingPoint (0602f0f0) looks up the cell, tests 0x10-byte bounds records and finds the quad by PointOnLineSide binary search.
- Sections are 0x16 bytes (width +0x10, heading +0x14); quads are 0xe bytes with 4 vertex offsets (3 shorts: x, height, z) plus normal/flag fields.
- track_GetSurfaceHeightAtPoint (0602f4a8): pick the quad triangle by diagonal, scanline-interpolate height in 12-bit fixed point. Slope comes from the quad normal shorts.
- car_LookupGroundMapValue (06029874): Morton-order (bit-interleaved) ground map lookup returning per-cell values for surface info.
- Body tilt (0602df7c) derives pitch/roll from the ground normal; likely cosmetic (GUESS, it is called last in the collision step).

## Jumps and airborne
- car_UpdateJumpTrigger (06034e70) fires jump triggers by proximity. Player jump launch scales with character field [7].
- Airborne: gravity each frame, car_UpdateVerticalBounce bounces on landing; car_CheckGroundContact decides contact by comparing car height with surface height; track_GetLowestGroundHeightAt gives the floor under overhangs.

## Surfaces (car_HandleSurfaceFlags 0602d16c)
Quad flag fields select special surfaces: water, speed pads, jump/boost triggers and soft walls. Exact bit meanings not fully decoded (GUESS: one bit water slowdown, one bit speed pad).

## Walls
- car_ResolveWallCollision (060308e0): tests the movement segment against wall segments with four PointOnLineSide tests; wall records are 0x10 bytes, 6-byte vertices.
- car_ComputeWallSlideVelocity (0602cf7c) is the slide response; car_ReflectOffWall (06030480) is the bounce: tangent velocity kept, normal component reflected and scaled (multiply by 0x55555556 >> 32, i.e. about 1/3, with a cap) and optionally pushed by the wall's bounce byte.
- Soft walls scale velocity by 3/4.
Net: glancing hits slide with little loss; head-on hits lose most normal speed.

## Car vs car
- car_CollideCarsSwept (06034b40): 16 substeps along the motion; radius sum from a short per car (DAT_06034d34 = 0x1b6 = 438 units); broad test uses (sum*3/4)^2.
- car_BounceCarsApart (060349a4): velocities multiplied by 14/16, then an impulse of (delta>>3) * clamp((speed sum)>>3, 7..0x14) >> 3 is exchanged.
- car_CollideCars (0602e32c): if closer than 0x60 pushes the pair apart.

## Rubber banding
- ai_UpdateRubberBand (06035974) runs per frame. It picks the rival car and computes d = (rival progress >> 21) - (player progress >> 21).
- With T = a global distance threshold (PTR_DAT_06035aac): d > T/2: scale = base/2 (floor 0x20); d > T/4: base*7/8 (floor 0x20); d < -T: base*5/4 (cap 0xc8 = 200); d < -T/2: base*3/2 (cap 0xc8); else base. Which sign means "ahead" is a GUESS.
- car_ApplyRubberBandStats (06035840) rescales accel, top speed and handling from that scale when it differs from the stored one and +0x5e < 3. ai_SelectSpeedCap (06035c34) sets the base by difficulty and level, floor 0x20.
- So the CPU speed scale spans roughly 50% to 200% of base by distance to the player.

## For Scorcher:
1. Store angle as 0..4095 and positions in 12-bit fixed with a 4096-entry sin/cos table. Cheap, deterministic, replay-friendly.
2. Record replays as one pad word per frame (end marker -1); the same trick gives ghosts and demo mode for free.
3. Per-character table of about 10 numbers (top speed, accel, steer rate, drag, grip, boost). Tune grip separately from steer rate so low grip gives a visible drift personality.
4. Keep forward and lateral speed separately and rotate to world each frame; drift is lateral speed above a threshold, decaying by a grip factor.
5. Ground = grid of cells -> track quads, triangle interpolation for height, normal from the quad.
6. Walls: slide for glancing hits, reflect with about 1/3 of the normal speed for head-on, so crashes cost speed without stopping dead.
7. Car-car: swept test in about 16 substeps so fast cars cannot tunnel, then 14/16 damping plus a clamped impulse. Avoids sticky and explosive bumps.
8. Rubber band as one scale on CPU stats (about 0.5x to 2x) driven by distance to the player, with floors and caps, no teleporting.
9. Rival AI steers toward waypoints with a capped turn step per frame; reads as human-like cornering.
10. Give CPU cars a cheaper path than the player (no pad logic, track-heading follow) to afford more cars.
