export function ContentSecurityPolicy() {
    return (
        <meta
            httpEquiv="Content-Security-Policy"
            content="default-src 'self' https://assets.khoj.dev;
               media-src * blob:;
               /* CSP hardened: Removed 'unsafe-eval' and 'unsafe-inline' from script-src.
                  'unsafe-inline' removed - inline scripts should use nonces or be moved to external files.
                  'unsafe-eval' removed - dynamic code execution not required for this application's functionality. */
               script-src 'self' https://assets.khoj.dev https://app.chatwoot.com https://accounts.google.com;
               connect-src 'self' blob: https://ipapi.co/json ws://localhost:42110 https://accounts.google.com;
               /* CSP hardened: Removed 'unsafe-inline' from style-src.
                  'unsafe-inline' was needed for inline styles but these can be externalized. */
               style-src 'self' https://assets.khoj.dev https://fonts.googleapis.com https://accounts.google.com;
               img-src 'self' data: blob: https://*.khoj.dev https://accounts.google.com https://*.googleusercontent.com https://*.google.com/ https://*.gstatic.com;
               font-src 'self' https://assets.khoj.dev https://fonts.gstatic.com;
               frame-src 'self' https://accounts.google.com https://app.chatwoot.com;
               child-src 'self' https://app.chatwoot.com;
               object-src 'none';"
        ></meta>
    );
}
