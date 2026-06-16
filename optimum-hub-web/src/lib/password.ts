/* xkcd-style password generator (mock only) - shared by New user, Profile and
 * Configure user so "Generate" reads the same everywhere. */
const WORDS = ['correct', 'horse', 'battery', 'staple', 'amber', 'cyan', 'lab', 'spawn', 'kernel', 'matrix', 'vector', 'tensor']

export function genPassword(): string {
  const t = Date.now()
  const pick = (n: number) => WORDS[(Math.floor(t / Math.pow(10, n)) + n) % WORDS.length]
  return `${pick(2)}-${pick(4)}-${pick(6)}-${pick(8)}`
}
