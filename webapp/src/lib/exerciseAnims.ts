// Анимации упражнений: позы фигурки и снаряды. Координаты кадра: 160 × 124,
// пол на y = 101, стоящая фигурка — таз (80, 54).
import type { Anim, Limb, Pt, Shape, SidePose } from './figure'

const stand = (arm: Limb, extra: Partial<SidePose> = {}): SidePose => ({
  hip: [80, 54],
  torso: -90,
  leg: [90, 90],
  arm,
  ...extra,
})

// Сцены
const FLAT_BENCH: Shape[] = [{ r: [38, 74, 70, 5] }, { l: [46, 79, 46, 101] }, { l: [100, 79, 100, 101] }]
const INCLINE_BENCH: Shape[] = [
  { r: [80, 76, 26, 5] },
  { l: [97, 77, 63, 49], w: 6 },
  { l: [92, 80, 92, 101] },
]
const SEAT: Shape[] = [{ r: [52, 76, 34, 5] }, { l: [69, 80, 69, 101] }]
const PULLUP_BAR: Shape[] = [{ l: [20, -8, 140, -8], w: 3 }]

// Лёжа на скамье на спине: плечо (65, 70)
const lying = (arm: Limb): SidePose => ({
  hip: [95, 70],
  torso: 180,
  leg: [20, 90],
  arm,
})
// Гриф идёт по прямой: от груди вверх над плечами
const benchPress: SidePose[] = [
  lying({ to: [65, 37], bend: -1 }),
  lying({ to: [64, 63], bend: -1 }),
]

// Сидя на наклонной скамье: плечо ≈ (72, 53)
const incline = (arm: Limb): SidePose => ({ hip: [95, 72], torso: -140, leg: [10, 90], arm })
const inclinePress: SidePose[] = [
  incline({ to: [72, 20], bend: -1 }),
  incline({ to: [75, 47], bend: -1 }),
]

// Приседание: стопы на месте, таз уходит назад-вниз
const squat = (arm: Limb, down: boolean, torso?: number): SidePose => ({
  hip: down ? [63, 78] : [80, 54],
  torso: torso ?? (down ? -52 : -88),
  leg: { to: [80, 100], bend: -1 },
  arm,
})

/** Педали: стопа по кругу вокруг каретки. */
function pedalFrames(base: Omit<SidePose, 'leg' | 'leg2'>, center: Pt, r: number): SidePose[] {
  return [0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
    const a = (i * Math.PI) / 4
    const p: Pt = [center[0] + r * Math.cos(a), center[1] + r * Math.sin(a)]
    const p2: Pt = [center[0] - r * Math.cos(a), center[1] - r * Math.sin(a)]
    return { ...base, leg: { to: p, bend: -1 }, leg2: { to: p2, bend: -1 } }
  })
}

/** Эллипсоид: стопы по эллипсу, руки на ручках — навстречу ногам. */
function ellipseFrames(): SidePose[] {
  return [0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
    const a = (i * Math.PI) / 4
    const c = Math.cos(a)
    const s = Math.sin(a)
    return {
      hip: [78, 50],
      torso: -88,
      leg: { to: [80 + 14 * c, 93 + 4 * s], bend: -1 },
      leg2: { to: [80 - 14 * c, 93 - 4 * s], bend: -1 },
      arm: { to: [96 - 8 * c, 46], bend: 1 },
      arm2: { to: [96 + 8 * c, 46], bend: 1 },
    }
  })
}

const run = (a: 1 | -1, treadmill = false): SidePose => {
  const y = treadmill ? 49 : 52
  const fwd: Limb = [60, 110]
  const back: Limb = [125, 165]
  const armFwd: Limb = [60, -30]
  const armBack: Limb = [125, 35]
  return {
    hip: [80, y],
    torso: -80,
    leg: a === 1 ? fwd : back,
    leg2: a === 1 ? back : fwd,
    foot: a === 1 ? -10 : 40,
    foot2: a === 1 ? 40 : -10,
    arm: a === 1 ? armBack : armFwd,
    arm2: a === 1 ? armFwd : armBack,
  }
}

const walk = (a: 1 | -1): SidePose => {
  const fwd: Limb = [70, 95]
  const back: Limb = [110, 110]
  return {
    hip: [80, 55],
    torso: -88,
    leg: a === 1 ? fwd : back,
    leg2: a === 1 ? back : fwd,
    foot: a === 1 ? -10 : 20,
    foot2: a === 1 ? 20 : -10,
    arm: a === 1 ? [110, 105] : [70, 60],
    arm2: a === 1 ? [70, 60] : [110, 105],
  }
}

const swim = (arm: Limb, arm2: Limb, kick: 1 | -1): SidePose => ({
  hip: [62, 60],
  torso: 0,
  head: 8,
  leg: [180 + 6 * kick, 180 - 6 * kick],
  leg2: [180 - 6 * kick, 180 + 6 * kick],
  foot: 180,
  foot2: 180,
  arm,
  arm2,
})

// Планка на прямых руках: стопы (27, 95), кисти (98, 101)
const pushUp = (up: boolean): SidePose =>
  up
    ? { hip: [70, 78.7], torso: -20.8, leg: [159.2, 159.2], foot: 65, arm: { to: [98, 100], bend: 1 } }
    : { hip: [72.6, 88.6], torso: -8, leg: [172, 172], foot: 60, arm: { to: [98, 100], bend: 1 } }

export const ANIMS = {
  benchBarbell: { view: 'side', frames: benchPress, scene: FLAT_BENCH, props: [{ t: 'plate', at: 'hand' }] },
  benchDb: { view: 'side', frames: benchPress, scene: FLAT_BENCH, props: [{ t: 'db', at: 'hand' }] },
  inclineBarbell: {
    view: 'side',
    frames: inclinePress,
    scene: INCLINE_BENCH,
    props: [{ t: 'plate', at: 'hand' }],
  },
  inclineDb: { view: 'side', frames: inclinePress, scene: INCLINE_BENCH, props: [{ t: 'db', at: 'hand' }] },
  // Вид со стороны ног: руки расходятся в стороны дугой
  flyDb: {
    view: 'front',
    noLegs: true,
    frames: [
      { hip: [80, 70], ts: 0.35, arm: [-95, -100] },
      { hip: [80, 70], ts: 0.35, arm: [5, 25] },
    ],
    scene: [{ r: [62, 72, 36, 6] }, { l: [68, 78, 68, 101] }, { l: [92, 78, 92, 101] }],
    props: [
      { t: 'db', at: 'hand' },
      { t: 'db', at: 'hand2' },
    ],
  },
  crossover: {
    view: 'front',
    frames: [
      { hip: [80, 54], arm: [-30, -10], leg: [84, 92] },
      { hip: [80, 54], arm: [110, 125], leg: [84, 92] },
    ],
    scene: [
      { l: [150, -10, 150, 101], w: 4 },
      { l: [10, -10, 10, 101], w: 4 },
    ],
    props: [
      { t: 'cable', at: 'hand', from: [148, -6] },
      { t: 'cable', at: 'hand2', from: [12, -6] },
    ],
  },
  pushUp: { view: 'side', frames: [pushUp(true), pushUp(false)] },
  dips: {
    view: 'side',
    frames: [
      { hip: [77.4, 48.9], torso: -85, leg: [100, 150], arm: { to: [80, 52], bend: 1 } },
      { hip: [71.7, 63.2], torso: -70, leg: [105, 155], arm: { to: [80, 52], bend: 1 } },
    ],
    scene: [{ l: [62, 54, 112, 54], w: 4 }, { l: [106, 54, 106, 101] }],
    floor: true,
  },
  chestPressMachine: {
    view: 'side',
    frames: [
      { hip: [70, 74], torso: -90, leg: [0, 90], arm: { to: [80, 49], bend: 1 } },
      { hip: [70, 74], torso: -90, leg: [0, 90], arm: { to: [102, 49], bend: 1 } },
    ],
    scene: [...SEAT, { l: [62, 76, 62, 32], w: 6 }, { l: [128, -2, 128, 101], w: 5 }],
    props: [{ t: 'seg', at: 'hand', angle: 90, len: 12 }],
  },
  pullUp: {
    view: 'front',
    floor: false,
    frames: [
      { hip: [80, 61], arm: [-75, -75], leg: [88, 94], ls: 0.85 },
      { hip: [80, 40], arm: [0, -121], leg: [88, 94], ls: 0.85 },
    ],
    scene: PULLUP_BAR,
  },
  latPulldown: {
    view: 'front',
    frames: [
      { hip: [80, 72], arm: [-70, -70], leg: [80, 92], ls: 0.62 },
      { hip: [80, 72], arm: [65, -80], leg: [80, 92], ls: 0.62 },
    ],
    scene: [{ r: [60, 74, 40, 5] }, { l: [80, 79, 80, 101] }],
    props: [{ t: 'bar', ext: 12 }, { t: 'cable', at: 'mid', from: [80, -12] }],
  },
  rowBarbell: {
    view: 'side',
    frames: [
      { hip: [66, 52], torso: -20, leg: { to: [80, 100], bend: -1 }, arm: [90, 90] },
      { hip: [66, 52], torso: -20, leg: { to: [80, 100], bend: -1 }, arm: [190, 80] },
    ],
    props: [{ t: 'plate', at: 'hand' }],
  },
  rowDb: {
    view: 'side',
    frames: [
      {
        hip: [60, 57],
        torso: -25,
        leg: [105, 75],
        leg2: [140, 180],
        foot2: 180,
        arm: [90, 90],
        arm2: [60, 60],
      },
      {
        hip: [60, 57],
        torso: -25,
        leg: [105, 75],
        leg2: [140, 180],
        foot2: 180,
        arm: [200, 80],
        arm2: [60, 60],
      },
    ],
    scene: [{ r: [14, 74, 98, 5] }, { l: [22, 79, 22, 101] }, { l: [104, 79, 104, 101] }],
    props: [{ t: 'db', at: 'hand' }],
  },
  rowCable: {
    view: 'side',
    frames: [
      { hip: [50, 88], torso: -80, leg: { to: [102, 94], bend: -1 }, foot: -70, arm: { to: [96, 72], bend: 1 } },
      { hip: [50, 88], torso: -95, leg: { to: [102, 94], bend: -1 }, foot: -70, arm: { to: [58, 74], bend: 1 } },
    ],
    scene: [{ r: [30, 92, 44, 5] }, { l: [106, 82, 108, 100], w: 4 }, { l: [140, 50, 140, 101], w: 5 }],
    props: [{ t: 'cable', at: 'hand', from: [138, 72] }, { t: 'seg', at: 'hand', angle: 90, len: 10 }],
  },
  deadlift: {
    view: 'side',
    frames: [
      { hip: [62, 72], torso: -38, leg: { to: [80, 100], bend: -1 }, arm: [90, 90] },
      { hip: [80, 54], torso: -90, leg: { to: [80, 100], bend: -1 }, arm: [90, 90] },
    ],
    ms: 1300,
    props: [{ t: 'plate', at: 'hand' }],
  },
  hyperext: {
    view: 'side',
    frames: [
      { hip: [78, 60], torso: 75, leg: [160, 160], foot: 90, arm: [225, 65] },
      { hip: [78, 60], torso: -20, leg: [160, 160], foot: 90, arm: [130, -30] },
    ],
    scene: [{ l: [72, 66, 90, 60], w: 7 }, { l: [70, 101, 82, 66] }, { c: [36, 82, 4], fill: true }, { l: [30, 101, 36, 82] }],
  },
  pullover: {
    view: 'side',
    frames: [lying([-90, -90]), lying([-170, -175])],
    scene: FLAT_BENCH,
    props: [{ t: 'db', at: 'hand' }],
  },
  ohpBarbell: {
    view: 'side',
    frames: [stand({ rel: [9, 5], bend: 1 }), stand({ rel: [1, -33], bend: 1 })],
    props: [{ t: 'plate', at: 'hand' }],
  },
  ohpDbSeated: {
    view: 'front',
    frames: [
      { hip: [80, 72], arm: [15, -90], leg: [80, 92], ls: 0.62 },
      { hip: [80, 72], arm: [-70, -80], leg: [80, 92], ls: 0.62 },
    ],
    scene: [{ r: [60, 74, 40, 5] }, { l: [80, 79, 80, 101] }],
    props: [
      { t: 'db', at: 'hand' },
      { t: 'db', at: 'hand2' },
    ],
  },
  lateralRaise: {
    view: 'front',
    frames: [
      { hip: [80, 54], arm: [82, 86], leg: [86, 92] },
      { hip: [80, 54], arm: [-3, 5], leg: [86, 92] },
    ],
    props: [
      { t: 'db', at: 'hand' },
      { t: 'db', at: 'hand2' },
    ],
  },
  rearRaise: {
    view: 'front',
    frames: [
      { hip: [80, 58], ts: 0.5, arm: [92, 92], leg: [84, 96] },
      { hip: [80, 58], ts: 0.5, arm: [5, 10], leg: [84, 96] },
    ],
    props: [
      { t: 'db', at: 'hand' },
      { t: 'db', at: 'hand2' },
    ],
  },
  frontRaise: {
    view: 'side',
    frames: [stand([85, 85]), stand([-3, -3])],
    props: [{ t: 'db', at: 'hand' }],
  },
  uprightRow: {
    view: 'front',
    frames: [
      { hip: [80, 54], arm: { to: [86, 58], bend: -1 }, leg: [86, 92] },
      { hip: [80, 54], arm: { to: [86, 30], bend: -1 }, leg: [86, 92] },
    ],
    props: [{ t: 'bar', ext: 14 }],
  },
  shrugs: {
    view: 'front',
    frames: [
      { hip: [80, 54], shrug: 0, arm: [80, 88], leg: [86, 92] },
      { hip: [80, 54], shrug: 8, arm: [80, 88], leg: [86, 92] },
    ],
    ms: 800,
    props: [
      { t: 'db', at: 'hand' },
      { t: 'db', at: 'hand2' },
    ],
  },
  curlBarbell: {
    view: 'side',
    frames: [stand([92, 92]), stand([95, -60])],
    props: [{ t: 'plate', at: 'hand' }],
  },
  curlDb: {
    view: 'side',
    frames: [stand([92, 92]), stand([95, -60])],
    props: [{ t: 'db', at: 'hand' }],
  },
  preacher: {
    view: 'side',
    frames: [
      { hip: [62, 76], torso: -80, leg: [10, 90], arm: [45, 40] },
      { hip: [62, 76], torso: -80, leg: [10, 90], arm: [45, -100] },
    ],
    scene: [{ r: [46, 78, 30, 5] }, { l: [60, 83, 60, 101] }, { l: [66, 52, 84, 70], w: 6 }, { l: [84, 70, 84, 101] }],
    props: [{ t: 'db', at: 'hand' }],
  },
  frenchPress: {
    view: 'side',
    frames: [lying([-100, -95]), lying([-100, 150])],
    scene: FLAT_BENCH,
    props: [{ t: 'seg', at: 'hand', angle: 90, len: 8 }],
  },
  pushdown: {
    view: 'side',
    frames: [stand([97, -25], { torso: -84 }), stand([97, 85], { torso: -84 })],
    scene: [{ l: [112, -12, 112, 101], w: 5 }],
    props: [{ t: 'cable', at: 'hand', from: [109, -6] }],
  },
  benchDips: {
    view: 'side',
    frames: [
      { hip: [57.6, 64], torso: -95, leg: { to: [104, 99], bend: -1 }, foot: -60, arm: { to: [50, 72], bend: 1 } },
      { hip: [57.6, 82], torso: -95, leg: { to: [104, 99], bend: -1 }, foot: -60, arm: { to: [50, 72], bend: 1 } },
    ],
    scene: [{ r: [14, 72, 40, 5] }, { l: [20, 77, 20, 101] }, { l: [48, 77, 48, 101] }],
  },
  squatBarbell: {
    view: 'side',
    frames: [squat({ rel: [4, -2], bend: -1 }, false), squat({ rel: [4, -2], bend: -1 }, true)],
    ms: 1300,
    props: [{ t: 'plate', at: 'shoulder', d: [-3, -4] }],
  },
  squatAir: {
    view: 'side',
    frames: [squat([85, 85], false), squat([-5, -5], true)],
  },
  squatGoblet: {
    view: 'side',
    frames: [squat({ rel: [8, 9], bend: 1 }, false), squat({ rel: [8, 9], bend: 1 }, true, -60)],
    props: [{ t: 'db', at: 'hand', d: [0, -1] }],
  },
  legPress: {
    view: 'side',
    frames: [
      { hip: [62, 82], torso: -150, leg: { to: [90, 50], bend: -1 }, foot: -45, arm: { to: [64, 86], bend: 1 } },
      { hip: [62, 82], torso: -150, leg: { to: [104, 36], bend: -1 }, foot: -45, arm: { to: [64, 86], bend: 1 } },
    ],
    ms: 1300,
    scene: [{ l: [34, 64, 58, 84], w: 6 }, { l: [56, 87, 76, 87], w: 6 }, { l: [70, 101, 140, 30], w: 3 }],
    props: [{ t: 'seg', at: 'foot', angle: 45, len: 22, d: [3, -3] }],
  },
  lunge: {
    view: 'side',
    frames: [
      { hip: [80, 54], torso: -90, leg: { to: [86, 99], bend: -1 }, leg2: { to: [74, 99], bend: -1 }, foot2: 0, arm: [90, 90] },
      { hip: [78, 74], torso: -90, leg: { to: [105, 99], bend: -1 }, leg2: { to: [52, 99], bend: -1 }, foot2: 30, arm: [90, 90] },
    ],
    props: [{ t: 'db', at: 'hand' }],
  },
  bulgarian: {
    view: 'side',
    frames: [
      { hip: [80, 56], torso: -88, leg: { to: [96, 99], bend: -1 }, leg2: { to: [44, 74], bend: -1 }, foot2: 160, arm: [90, 90] },
      { hip: [74, 76], torso: -78, leg: { to: [96, 99], bend: -1 }, leg2: { to: [44, 74], bend: -1 }, foot2: 160, arm: [90, 90] },
    ],
    scene: [{ r: [18, 76, 32, 5] }, { l: [24, 81, 24, 101] }, { l: [44, 81, 44, 101] }],
    props: [{ t: 'db', at: 'hand' }],
  },
  rdl: {
    view: 'side',
    frames: [
      { hip: [80, 54], torso: -90, leg: { to: [80, 100], bend: -1 }, arm: [90, 90] },
      { hip: [66, 57], torso: -15, leg: { to: [80, 100], bend: -1 }, arm: [90, 90] },
    ],
    ms: 1300,
    props: [{ t: 'plate', at: 'hand' }],
  },
  legExtension: {
    view: 'side',
    frames: [
      { hip: [60, 70], torso: -95, leg: [0, 95], foot: 5, arm: [100, 30] },
      { hip: [60, 70], torso: -95, leg: [0, 5], foot: -80, arm: [100, 30] },
    ],
    scene: [{ r: [44, 72, 40, 5] }, { l: [49, 72, 46, 38], w: 6 }, { l: [62, 77, 62, 101] }],
    props: [{ t: 'pad', at: 'foot', d: [2, 0] }],
  },
  legCurl: {
    view: 'side',
    frames: [
      { hip: [80, 70], torso: 180, head: -10, leg: [0, 0], foot: 90, arm: [100, 90] },
      { hip: [80, 70], torso: 180, head: -10, leg: [0, -110], foot: -20, arm: [100, 90] },
    ],
    scene: [{ r: [30, 74, 80, 5] }, { l: [40, 79, 40, 101] }, { l: [100, 79, 100, 101] }],
    props: [{ t: 'pad', at: 'foot', d: [0, 3] }],
  },
  hipThrust: {
    view: 'side',
    frames: [
      { hip: [60, 92], torso: -132, leg: { to: [96, 99], bend: -1 }, arm: { to: [64, 86], bend: 1 } },
      { hip: [68, 74], torso: -166, leg: { to: [96, 99], bend: -1 }, arm: { to: [70, 68], bend: 1 } },
    ],
    scene: [{ r: [14, 70, 28, 6] }, { l: [20, 76, 20, 101] }, { l: [36, 76, 36, 101] }],
    props: [{ t: 'plate', at: 'hip', d: [0, -8] }],
  },
  calfRaise: {
    view: 'side',
    frames: [stand([90, 90], { foot: 0 }), stand([90, 90], { hip: [80, 48], foot: 40 })],
    ms: 800,
    props: [{ t: 'db', at: 'hand' }],
  },
  crunch: {
    view: 'side',
    frames: [
      { hip: [72, 96], torso: -180, leg: { to: [100, 99], bend: -1 }, arm: { rel: [-5, -10], bend: -1 } },
      { hip: [72, 96], torso: -150, head: 15, leg: { to: [100, 99], bend: -1 }, arm: { rel: [-5, -10], bend: -1 } },
    ],
  },
  hangingLegRaise: {
    view: 'side',
    floor: false,
    frames: [
      { hip: [80, 55], torso: -90, leg: [92, 92], arm: { to: [80, -8], bend: 1 } },
      { hip: [80, 55], torso: -95, leg: [-5, -5], foot: -60, arm: { to: [80, -8], bend: 1 } },
    ],
    scene: PULLUP_BAR,
  },
  reverseCrunch: {
    view: 'side',
    frames: [
      { hip: [75, 96], torso: 180, leg: { to: [104, 92], bend: -1 }, arm: [5, 0] },
      { hip: [72, 92], torso: 175, leg: { to: [72, 66], bend: -1 }, arm: [5, 0] },
    ],
  },
  russianTwist: {
    view: 'front',
    frames: [
      { hip: [80, 90], ts: 0.75, leg: [40, 110], ls: 0.7, arm: { to: [104, 82], bend: 1 }, arm2: { to: [98, 82], bend: 1 } },
      { hip: [80, 90], ts: 0.75, leg: [40, 110], ls: 0.7, arm: { to: [62, 82], bend: -1 }, arm2: { to: [56, 82], bend: -1 } },
    ],
    props: [{ t: 'kb', at: 'mid', d: [0, -8] }],
  },
  plank: {
    view: 'side',
    frames: [
      { hip: [75, 87], torso: -11.3, leg: [168.7, 168.7], foot: 65, arm: [90, 0] },
      { hip: [75, 86], torso: -12, leg: [168, 168], foot: 65, arm: [90, 0] },
    ],
    ms: 1500,
  },
  sidePlank: {
    view: 'side',
    frames: [
      { hip: [75, 90], torso: -14, leg: [171, 171], foot: 80, arm: [-90, -90], arm2: [90, 0] },
      { hip: [75, 84], torso: -11, leg: [168, 168], foot: 80, arm: [-90, -90], arm2: [90, 0] },
    ],
    ms: 1300,
  },
  burpee: {
    view: 'side',
    frames: [
      stand([90, 90], { foot: 0 }),
      { hip: [72, 82], torso: -40, leg: [-20, 110], foot: 0, arm: [85, 85] },
      { hip: [70, 78.7], torso: -20.8, leg: [159.2, 159.2], foot: 65, arm: [90, 90] },
      { hip: [72, 82], torso: -40, leg: [-20, 110], foot: 0, arm: [85, 85] },
      stand([-90, -90], { hip: [80, 44], foot: 30 }),
    ],
    ms: 600,
  },
  kbSwing: {
    view: 'side',
    frames: [
      { hip: [68, 58], torso: -28, leg: { to: [80, 100], bend: -1 }, arm: [115, 115] },
      { hip: [80, 54], torso: -92, leg: { to: [80, 100], bend: -1 }, arm: [-5, -5] },
    ],
    ms: 800,
    props: [{ t: 'kb', at: 'hand' }],
  },
  kbPress: {
    view: 'side',
    frames: [
      { hip: [78, 62], torso: -88, leg: { to: [80, 100], bend: -1 }, arm: { rel: [7, 4], bend: 1 } },
      { hip: [80, 54], torso: -90, leg: { to: [80, 100], bend: -1 }, arm: { rel: [2, -33], bend: 1 } },
    ],
    ms: 900,
    props: [{ t: 'kb', at: 'hand', d: [0, -8] }],
  },
  run: { view: 'side', frames: [run(1), run(-1)], ms: 380, linear: true },
  treadmill: {
    view: 'side',
    frames: [run(1, true), run(-1, true)],
    ms: 380,
    linear: true,
    scene: [{ r: [24, 96, 112, 5] }, { l: [132, 96, 142, 44], w: 3 }, { l: [142, 44, 128, 42], w: 3 }],
  },
  walk: { view: 'side', frames: [walk(1), walk(-1)], ms: 650 },
  bike: {
    view: 'side',
    frames: pedalFrames({ hip: [70, 52], torso: -42, arm: { to: [110, 48], bend: 1 } }, [84, 84], 9),
    ms: 160,
    linear: true,
    scene: [
      { c: [44, 86, 15] },
      { c: [122, 86, 15] },
      { l: [44, 86, 84, 84], w: 2.5 },
      { l: [84, 84, 66, 58], w: 2.5 },
      { l: [66, 58, 112, 56], w: 2.5 },
      { l: [84, 84, 112, 56], w: 2.5 },
      { l: [112, 56, 122, 86], w: 2.5 },
      { l: [62, 55, 76, 55], w: 4 },
      { l: [110, 46, 112, 56], w: 2.5 },
    ],
  },
  bikeStationary: {
    view: 'side',
    frames: pedalFrames({ hip: [70, 52], torso: -55, arm: { to: [110, 50], bend: 1 } }, [84, 84], 9),
    ms: 160,
    linear: true,
    scene: [
      { l: [40, 101, 130, 101], w: 5 },
      { l: [70, 56, 84, 84], w: 3 },
      { l: [84, 84, 76, 101], w: 3 },
      { c: [102, 82, 11] },
      { l: [104, 101, 110, 50], w: 3 },
      { l: [62, 55, 76, 55], w: 4 },
    ],
  },
  elliptical: {
    view: 'side',
    frames: ellipseFrames(),
    ms: 180,
    linear: true,
    scene: [{ l: [40, 101, 140, 101], w: 5 }, { l: [120, 101, 112, 30], w: 3 }],
  },
  rower: {
    view: 'side',
    frames: [
      { hip: [72, 88], torso: -55, leg: { to: [110, 90], bend: -1 }, foot: -70, arm: { to: [118, 76], bend: 1 } },
      { hip: [48, 88], torso: -105, leg: { to: [110, 90], bend: -1 }, foot: -70, arm: { to: [54, 72], bend: 1 } },
    ],
    ms: 900,
    scene: [{ l: [16, 96, 132, 96], w: 3 }, { c: [134, 82, 10] }, { l: [110, 80, 114, 96], w: 3 }],
    props: [
      { t: 'cable', at: 'hand', from: [128, 80] },
      { t: 'seg', at: 'hip', angle: 0, len: 18, d: [0, 4] },
    ],
  },
  swim: {
    view: 'side',
    floor: false,
    frames: [
      swim([-15, -5], [100, 95], 1),
      swim([90, 100], [170, 170], -1),
      swim([170, 170], [-100, -40], 1),
      swim([-100, -40], [-15, -5], -1),
    ],
    ms: 500,
    linear: true,
    scene: [{ l: [0, 54, 160, 54], w: 1.5 }],
  },
  jumpRope: {
    view: 'side',
    frames: [
      stand([100, 20], { foot: 0, rope: [76, -16] }),
      stand([100, 20], { hip: [80, 50], foot: 20, rope: [140, 60] }),
      stand([100, 20], { hip: [80, 46], foot: 30, rope: [80, 110] }),
      stand([100, 20], { hip: [80, 51], foot: 10, rope: [20, 60] }),
    ],
    ms: 200,
    linear: true,
    props: [{ t: 'rope' }],
  },
  stepper: {
    view: 'side',
    frames: [
      { hip: [78, 52], torso: -84, leg: { to: [86, 86], bend: -1 }, leg2: { to: [80, 98], bend: -1 }, arm: { to: [100, 50], bend: 1 } },
      { hip: [78, 52], torso: -84, leg: { to: [86, 98], bend: -1 }, leg2: { to: [80, 86], bend: -1 }, arm: { to: [100, 50], bend: 1 } },
    ],
    ms: 500,
    scene: [{ l: [40, 101, 130, 101], w: 5 }, { l: [118, 101, 110, 46], w: 3 }, { l: [110, 48, 98, 50], w: 3 }],
  },
  stretchFull: {
    view: 'side',
    frames: [stand([-90, -90]), stand([95, 95], { torso: 80 })],
    ms: 1800,
  },
  stretchHamstring: {
    view: 'side',
    frames: [
      { hip: [50, 96], torso: -80, leg: [0, 0], foot: -80, arm: { to: [72, 92], bend: 1 } },
      { hip: [50, 96], torso: -22, leg: [0, 0], foot: -80, arm: { to: [100, 90], bend: 1 } },
    ],
    ms: 1800,
  },
  stretchChest: {
    view: 'side',
    frames: [stand([100, 100], { torso: -88 }), stand([150, 160], { torso: -80 })],
    ms: 1800,
  },
  childPose: {
    view: 'side',
    frames: [
      { hip: [70, 86], torso: -88, leg: { to: [62, 98], bend: -1 }, foot: 180, arm: { to: [78, 90], bend: 1 } },
      { hip: [70, 86], torso: 12, head: 5, leg: { to: [62, 98], bend: -1 }, foot: 180, arm: { to: [134, 98], bend: 1 } },
    ],
    ms: 1800,
  },
  yoga: {
    view: 'side',
    frames: [
      { hip: [80, 54], torso: -90, leg: { to: [74, 100], bend: -1 }, arm: { to: [81, -9], bend: 1 } },
      { hip: [80, 54], torso: 82, leg: { to: [74, 100], bend: -1 }, arm: { to: [88, 100], bend: 1 } },
      { hip: [88, 58], torso: 48, head: 20, leg: { to: [70, 100], bend: -1 }, foot: 10, arm: { to: [126, 100], bend: 1 } },
    ],
    ms: 1600,
  },
} satisfies Record<string, Anim>

export type AnimId = keyof typeof ANIMS
