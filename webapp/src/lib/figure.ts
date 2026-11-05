// Движок анимированной фигурки для карточек техники упражнений.
// Фигурка — «скелет» из отрезков. Поза задаётся углами суставов или точкой, куда тянется
// кисть/стопа (обратная кинематика). Анимация — плавный переход между позами по кругу.
// Модуль без зависимостей: его же использует скрипт предпросмотра поз.

export type Pt = [number, number]

/** Конечность: углы [плечо/бедро, предплечье/голень] в градусах (0 — вправо, 90 — вниз),
 * либо точка, куда тянется кисть/стопа: `to` — в координатах кадра, `rel` — от плеча/таза.
 * `bend` — в какую сторону сгибается локоть/колено (1 или -1). */
export type Limb = [number, number] | { to: Pt; bend: number } | { rel: Pt; bend: number }

/** Вид сбоку: фигурка смотрит вправо. Вторые конечности (дальние) рисуются бледнее. */
export interface SidePose {
  hip: Pt
  torso: number
  head?: number
  leg: Limb
  leg2?: Limb
  foot?: number
  foot2?: number
  arm: Limb
  arm2?: Limb
  /** Точка верёвки скакалки (контрольная точка кривой). */
  rope?: Pt
}

/** Вид спереди: задаётся правая (на экране) сторона, левая — зеркально. */
export interface FrontPose {
  hip: Pt
  /** Видимая длина корпуса (наклон к зрителю укорачивает его). */
  ts?: number
  /** Подъём плеч (шраги), px. */
  shrug?: number
  arm: Limb
  /** Своя левая рука вместо зеркальной. */
  arm2?: Limb
  leg?: Limb
  /** Видимая длина ног. */
  ls?: number
}

export type Shape =
  | { l: [number, number, number, number]; w?: number }
  | { r: [number, number, number, number] }
  | { c: [number, number, number]; fill?: boolean }

export type Joint = 'hand' | 'hand2' | 'mid' | 'foot' | 'foot2' | 'shoulder' | 'hip' | 'knee'

export type Prop =
  | { t: 'plate' | 'db' | 'kb' | 'pad'; at: Joint; d?: Pt }
  | { t: 'cable'; at: Joint; from: Pt }
  | { t: 'seg'; at: Joint; angle: number; len: number; d?: Pt }
  | { t: 'bar'; ext: number }
  | { t: 'rope' }

interface AnimBase {
  scene?: Shape[]
  props?: Prop[]
  /** Длительность перехода между соседними позами, мс. */
  ms?: number
  /** Равномерное движение без замедления у поз — для циклов (бег, педали). */
  linear?: boolean
  floor?: boolean
}

export type Anim =
  | (AnimBase & { view: 'side'; frames: SidePose[] })
  | (AnimBase & { view: 'front'; frames: FrontPose[]; noLegs?: boolean })

/** Примитивы для отрисовки. role: body — фигурка, far — дальние конечности, scene, prop. */
export type Prim =
  | { k: 'line'; p: [number, number, number, number]; w: number; role: Role }
  | { k: 'circle'; p: [number, number, number]; role: Role; fill: boolean; w?: number }
  | { k: 'path'; d: string; w: number; role: Role }

export type Role = 'body' | 'far' | 'scene' | 'prop'

// Длины сегментов, px в координатах кадра
const TORSO = 30
const NECK = 11
const HEAD_R = 7
const UPPER_ARM = 17
const FOREARM = 16
const THIGH = 23
const SHIN = 23
const FOOT = 8
const SHOULDER_HALF = 11
const HIP_HALF = 6
const BODY_W = 5

export const VIEW_BOX = '0 -14 160 124'
const FLOOR_Y = 101

const rad = (deg: number) => (deg * Math.PI) / 180
const add = (p: Pt, len: number, deg: number): Pt => [
  p[0] + len * Math.cos(rad(deg)),
  p[1] + len * Math.sin(rad(deg)),
]

/** Двухзвенная конечность от base: возвращает [сустав, конец]. */
function limb(base: Pt, l: Limb, a: number, b: number): [Pt, Pt] {
  if (Array.isArray(l)) {
    const j = add(base, a, l[0])
    return [j, add(j, b, l[1])]
  }
  const target: Pt = 'to' in l ? l.to : [base[0] + l.rel[0], base[1] + l.rel[1]]
  const dx = target[0] - base[0]
  const dy = target[1] - base[1]
  // Недостижимую точку тянемся прямой рукой, слишком близкую — сгибаем до предела
  const d = Math.min(Math.max(Math.hypot(dx, dy), Math.abs(a - b) + 0.5), a + b - 0.01)
  const baseAngle = (Math.atan2(dy, dx) * 180) / Math.PI
  const alpha = (Math.acos((a * a + d * d - b * b) / (2 * a * d)) * 180) / Math.PI
  const j = add(base, a, baseAngle + l.bend * alpha)
  const end = add(base, d, baseAngle)
  return [j, end]
}

const lerp = (a: number, b: number, u: number) => a + (b - a) * u
const lerpPt = (a: Pt, b: Pt, u: number): Pt => [lerp(a[0], b[0], u), lerp(a[1], b[1], u)]

function lerpLimb(a: Limb, b: Limb, u: number): Limb {
  if (Array.isArray(a) && Array.isArray(b)) return [lerp(a[0], b[0], u), lerp(a[1], b[1], u)]
  if (!Array.isArray(a) && !Array.isArray(b)) {
    if ('to' in a && 'to' in b) return { to: lerpPt(a.to, b.to, u), bend: a.bend }
    if ('rel' in a && 'rel' in b) return { rel: lerpPt(a.rel, b.rel, u), bend: a.bend }
  }
  // Разные формы в соседних позах — без перехода (ошибка в данных, проверяется скриптом)
  return u < 0.5 ? a : b
}

function lerpObj<T extends object>(a: T, b: T, u: number): T {
  const out: Record<string, unknown> = {}
  for (const key of Object.keys(a) as (keyof T & string)[]) {
    const va = a[key] as unknown
    const vb = (b[key] ?? va) as unknown
    if (typeof va === 'number') out[key] = lerp(va, vb as number, u)
    else if (key === 'hip' || key === 'rope') out[key] = lerpPt(va as Pt, vb as Pt, u)
    else out[key] = lerpLimb(va as Limb, vb as Limb, u)
  }
  return out as T
}

/** Поза в момент t (мс) — переход между кадрами по кругу. */
function poseAt<T extends object>(frames: T[], t: number, ms: number, linear: boolean): T {
  const n = frames.length
  const pos = (t / ms) % n
  const i = Math.floor(pos)
  const f = pos - i
  // Без linear — замедление у крайних поз, как в живом движении
  const u = linear ? f : (1 - Math.cos(Math.PI * f)) / 2
  return lerpObj(frames[i], frames[(i + 1) % n], u)
}

export function cycleMs(anim: Anim): number {
  return (anim.ms ?? 1100) * anim.frames.length
}

const line = (a: Pt, b: Pt, role: Role, w = BODY_W): Prim => ({
  k: 'line',
  p: [a[0], a[1], b[0], b[1]],
  w,
  role,
})

function sceneLayer(anim: Anim): Prim[] {
  const out: Prim[] = []
  if (anim.floor !== false) out.push({ k: 'line', p: [6, FLOOR_Y + 2, 154, FLOOR_Y + 2], w: 1.5, role: 'scene' })
  for (const s of anim.scene ?? []) {
    if ('l' in s) out.push({ k: 'line', p: s.l, w: s.w ?? 3, role: 'scene' })
    else if ('c' in s) out.push({ k: 'circle', p: s.c, role: 'scene', fill: s.fill ?? false, w: 2 })
    else {
      const [x, y, w, h] = s.r
      // Прямоугольник — толстая линия по длинной стороне
      out.push(
        w >= h
          ? { k: 'line', p: [x, y + h / 2, x + w, y + h / 2], w: h, role: 'scene' }
          : { k: 'line', p: [x + w / 2, y, x + w / 2, y + h], w, role: 'scene' },
      )
    }
  }
  return out
}

function propLayer(props: Prop[] | undefined, joints: Partial<Record<Joint, Pt>>, rope?: Pt): Prim[] {
  const out: Prim[] = []
  const at = (j: Joint, d?: Pt): Pt | null => {
    const p = joints[j]
    return p ? [p[0] + (d?.[0] ?? 0), p[1] + (d?.[1] ?? 0)] : null
  }
  for (const pr of props ?? []) {
    if (pr.t === 'bar') {
      const h = joints.hand
      const h2 = joints.hand2
      if (!h || !h2) continue
      const lx = Math.min(h[0], h2[0]) - pr.ext
      const rx = Math.max(h[0], h2[0]) + pr.ext
      const y = (h[1] + h2[1]) / 2
      out.push({ k: 'line', p: [lx, y, rx, y], w: 2.5, role: 'prop' })
      out.push({ k: 'line', p: [lx + 3, y - 8, lx + 3, y + 8], w: 5, role: 'prop' })
      out.push({ k: 'line', p: [rx - 3, y - 8, rx - 3, y + 8], w: 5, role: 'prop' })
      continue
    }
    if (pr.t === 'rope') {
      const h = joints.hand
      if (!h || !rope) continue
      // Петля: две контрольные точки по обе стороны от направления на верёвку
      const dx = rope[0] - h[0]
      const dy = rope[1] - h[1]
      const len = Math.hypot(dx, dy) || 1
      const px = (-dy / len) * 22
      const py = (dx / len) * 22
      const cx = h[0] + dx * 1.3
      const cy = h[1] + dy * 1.3
      out.push({
        k: 'path',
        d: `M${h[0]} ${h[1]} C${cx + px} ${cy + py} ${cx - px} ${cy - py} ${h[0]} ${h[1]}`,
        w: 1.5,
        role: 'prop',
      })
      continue
    }
    const p = at(pr.at, 'd' in pr ? pr.d : undefined)
    if (!p) continue
    if (pr.t === 'plate') out.push({ k: 'circle', p: [p[0], p[1], 9], role: 'prop', fill: true })
    else if (pr.t === 'db') {
      out.push({ k: 'line', p: [p[0] - 5, p[1], p[0] + 5, p[1]], w: 2.5, role: 'prop' })
      out.push({ k: 'circle', p: [p[0] - 5, p[1], 3.5], role: 'prop', fill: true })
      out.push({ k: 'circle', p: [p[0] + 5, p[1], 3.5], role: 'prop', fill: true })
    } else if (pr.t === 'kb') {
      out.push({ k: 'circle', p: [p[0], p[1] + 8, 6], role: 'prop', fill: true })
      out.push({ k: 'line', p: [p[0], p[1], p[0], p[1] + 4], w: 2, role: 'prop' })
    } else if (pr.t === 'pad') out.push({ k: 'circle', p: [p[0], p[1], 4.5], role: 'scene', fill: true })
    else if (pr.t === 'cable') {
      out.push({ k: 'line', p: [pr.from[0], pr.from[1], p[0], p[1]], w: 1.2, role: 'scene' })
      out.push({ k: 'circle', p: [pr.from[0], pr.from[1], 3], role: 'scene', fill: true })
    } else if (pr.t === 'seg') {
      const a = add(p, pr.len / 2, pr.angle + 180)
      const b = add(p, pr.len / 2, pr.angle)
      out.push(line(a, b, 'scene', 4))
    }
  }
  return out
}

function drawSide(anim: Anim & { view: 'side' }, pose: SidePose): Prim[] {
  const hip = pose.hip
  const shoulder = add(hip, TORSO, pose.torso)
  const head = add(shoulder, NECK, pose.torso + (pose.head ?? 0))
  const [knee, ankle] = limb(hip, pose.leg, THIGH, SHIN)
  const [elbow, hand] = limb(shoulder, pose.arm, UPPER_ARM, FOREARM)
  const out: Prim[] = []
  const joints: Partial<Record<Joint, Pt>> = { hip, shoulder, knee, foot: ankle, hand }

  if (pose.leg2) {
    const [k2, a2] = limb(hip, pose.leg2, THIGH, SHIN)
    joints.foot2 = a2
    out.push(line(hip, k2, 'far'), line(k2, a2, 'far'), line(a2, add(a2, FOOT, pose.foot2 ?? 0), 'far', 4))
  }
  if (pose.arm2) {
    const [e2, h2] = limb(shoulder, pose.arm2, UPPER_ARM, FOREARM)
    joints.hand2 = h2
    out.push(line(shoulder, e2, 'far'), line(e2, h2, 'far'))
  }
  out.push(
    line(hip, knee, 'body'),
    line(knee, ankle, 'body'),
    line(ankle, add(ankle, FOOT, pose.foot ?? 0), 'body', 4),
    line(hip, shoulder, 'body', 6),
    { k: 'circle', p: [head[0], head[1], HEAD_R], role: 'body', fill: true },
    line(shoulder, elbow, 'body'),
    line(elbow, hand, 'body'),
  )
  return [...sceneLayer(anim), ...out, ...propLayer(anim.props, joints, pose.rope)]
}

/** Зеркальная (левая) конечность для вида спереди. */
function mirror(l: Limb, cx: number): Limb {
  if (Array.isArray(l)) return [180 - l[0], 180 - l[1]]
  if ('to' in l) return { to: [2 * cx - l.to[0], l.to[1]], bend: -l.bend }
  return { rel: [-l.rel[0], l.rel[1]], bend: -l.bend }
}

function drawFront(anim: Anim & { view: 'front' }, pose: FrontPose): Prim[] {
  const [cx, hy] = pose.hip
  const sy = hy - TORSO * (pose.ts ?? 1)
  const lift = pose.shrug ?? 0
  const sR: Pt = [cx + SHOULDER_HALF, sy - lift]
  const sL: Pt = [cx - SHOULDER_HALF, sy - lift]
  const head: Pt = [cx, sy - NECK]
  const [eR, hR] = limb(sR, pose.arm, UPPER_ARM, FOREARM)
  const [eL, hL] = limb(sL, pose.arm2 ?? mirror(pose.arm, cx), UPPER_ARM, FOREARM)
  const out: Prim[] = []
  const joints: Partial<Record<Joint, Pt>> = {
    hip: pose.hip,
    shoulder: [cx, sy],
    hand: hR,
    hand2: hL,
    mid: [(hR[0] + hL[0]) / 2, (hR[1] + hL[1]) / 2],
  }
  if (!anim.noLegs && pose.leg) {
    const s = pose.ls ?? 1
    const hipR: Pt = [cx + HIP_HALF, hy]
    const hipL: Pt = [cx - HIP_HALF, hy]
    const [kR, aR] = limb(hipR, pose.leg, THIGH * s, SHIN * s)
    const [kL, aL] = limb(hipL, mirror(pose.leg, cx), THIGH * s, SHIN * s)
    joints.foot = aR
    joints.foot2 = aL
    out.push(
      line(hipL, hipR, 'body'),
      line(hipR, kR, 'body'),
      line(kR, aR, 'body'),
      line(hipL, kL, 'body'),
      line(kL, aL, 'body'),
      line(aR, [aR[0] + 5, aR[1]], 'body', 4),
      line(aL, [aL[0] - 5, aL[1]], 'body', 4),
    )
  }
  out.push(
    line(pose.hip, [cx, sy], 'body', 7),
    line(sL, sR, 'body'),
    { k: 'circle', p: [head[0], head[1], HEAD_R], role: 'body', fill: true },
    line(sR, eR, 'body'),
    line(eR, hR, 'body'),
    line(sL, eL, 'body'),
    line(eL, hL, 'body'),
  )
  return [...sceneLayer(anim), ...out, ...propLayer(anim.props, joints)]
}

/** Кадр анимации в момент t (мс). */
export function drawAt(anim: Anim, t: number): Prim[] {
  const ms = anim.ms ?? 1100
  const linear = anim.linear ?? false
  if (anim.view === 'side') return drawSide(anim, poseAt(anim.frames, t, ms, linear))
  return drawFront(anim, poseAt(anim.frames, t, ms, linear))
}

/** Проверка данных: у соседних поз конечности заданы в одной форме. */
export function checkAnim(anim: Anim): string[] {
  const errors: string[] = []
  const form = (l: unknown) =>
    l === undefined ? 'none' : Array.isArray(l) ? 'angles' : 'to' in (l as object) ? 'to' : 'rel'
  const frames = anim.frames as unknown as Record<string, unknown>[]
  for (const key of ['leg', 'leg2', 'arm', 'arm2']) {
    const forms = new Set(frames.map((f) => form(f[key])))
    if (forms.size > 1) errors.push(`${key}: разные формы ${[...forms].join(', ')}`)
  }
  return errors
}
