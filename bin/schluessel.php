<?php

declare(strict_types=1);

// Erzeugt einen neuen Hauptschlüssel für APP_SCHLUESSEL in der .env.
echo 'APP_SCHLUESSEL=base64:' . base64_encode(random_bytes(32)) . PHP_EOL;
