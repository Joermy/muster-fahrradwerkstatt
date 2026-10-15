<?php

declare(strict_types=1);

/*
 * Sicherheitsköpfe für alle Seiten. Dieselben Werte stehen in public/.htaccess und
 * konfig/nginx.conf; bin/pruefen.php vergleicht, dass alle drei übereinstimmen.
 *
 * 'wasm-unsafe-eval' braucht der Meshopt-Decoder für das 3D-Modell (WebAssembly),
 * normales eval() bleibt verboten. Karten von OpenStreetMap laden nur nach Klick.
 */
return [
    'Content-Security-Policy' => "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src https://www.openstreetmap.org; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    'X-Content-Type-Options' => 'nosniff',
    'Referrer-Policy' => 'strict-origin-when-cross-origin',
    'Permissions-Policy' => 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
    'Cross-Origin-Opener-Policy' => 'same-origin',
    'X-Frame-Options' => 'DENY',
];
