/**
 * Mark on a Projet-attested skill tag.
 *
 * Drop your PNG at `apps/web/public/projet-mark.png` — Next serves it at
 * `/projet-mark.png`. Replace that file; do not upload it through the app.
 */
export const PROJET_MARK_SRC = "/projet-mark.png";

export default function ProjetVerifiedStamp() {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className="skill-stamp"
      src={PROJET_MARK_SRC}
      alt=""
      title="Projet Verified"
    />
  );
}
