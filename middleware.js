// Passwortschutz (Basic Auth) fuer den ganzen Radar. Passwort steht als RADAR_PASSWORD in den Vercel-Umgebungsvariablen.
export const config = { matcher: '/:path*' };

export default function middleware(request) {
  const expected = process.env.RADAR_PASSWORD;
  const [scheme, encoded] = (request.headers.get('authorization') || '').split(' ');
  if (expected && scheme === 'Basic' && encoded) {
    const decoded = atob(encoded);
    if (decoded.slice(decoded.indexOf(':') + 1) === expected) return; // durchlassen
  }
  return new Response('Bitte mit dem Passwort anmelden.', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="Chancen-Radar", charset="UTF-8"', 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
