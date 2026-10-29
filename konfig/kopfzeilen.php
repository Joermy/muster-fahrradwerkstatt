<?php

declare(strict_types=1);

/*
 * Sicherheitsköpfe für alle Seiten. Dieselben Werte stehen in public/.htaccess und
 * konfig/nginx.conf; bin/pruefen.php vergleicht, dass alle drei übereinstimmen.
 *
 * Die Werkstatt auf der Startseite ist eine Bildfolge im Canvas: kein WebAssembly, keine Worker,
 * kein eval(). Karten von OpenStreetMap laden nur nach Klick.
 */
return [
    'Content-Security-Policy' => "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src https://www.openstreetmap.org; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    'X-Content-Type-Options' => 'nosniff',
    'Referrer-Policy' => 'strict-origin-when-cross-origin',
    'Permissions-Policy' => 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
    'Cross-Origin-Opener-Policy' => 'same-origin',
    'X-Frame-Options' => 'DENY',
];
