# Clear Download Manager Extension 0.45.12

Compatibilidad con CDM 0.95.x: el release público de la aplicación está en
`https://github.com/CacaPlay/clear-download-manager-releases/releases/tag/v0.95.0`.
La extensión se distribuye exclusivamente mediante Chrome Web Store; este
paquete se usa para actualizar la ficha existente.

El build inyecta, únicamente en el paquete generado, la clave pública recuperada en `evidence/official-public-key.json`; así el unpacked conserva el ID oficial `aonppfnabjnicjjeoofkfjofolfibggp`. Es una clave de identidad pública, no una firma privada. El host oficial y el alias QA del equipo permanecen separados y no se sustituyen desde esta build.

## Cambios

- Mix de YouTube: conservar el vídeo de origen y list=RD... en la URL de reproducción.
- Botón + para añadir vídeos/audio a playlists manuales, con metadatos y sin duplicados.
- Enviar a Clear Download Manager con el menú contextual y su icono. Vídeo/audio/página/enlace: preparación en primer plano. Imagen HTTP(S): envío en segundo plano. Imágenes blob/data: rechazo explícito.
- Mejor calidad mantiene auto sin techo fijo de 1080p; depende de la fuente.
- Texto, secciones y miniaturas más grandes y adaptables. El ancho exterior del panel lo controla el navegador mediante su divisor.
- Cuatro colores independientes de progreso; se informa cuando la app no los publica.
- Controles según capacidades y estado reciente; ACK significa solicitud recibida, no ejecutada.
- Registro persistente de reenvíos inciertos. No equivale a exactly-once en el backend.
- Miniaturas con tiempo acotado y sin alterar URLs firmadas.

## Captura segura

Las instalaciones nuevas inician en Automático y conservan preferencias existentes. La captura automática ignora incógnito y consulta capacidades antes de pausar. Solo cancela en navegador tras accepted. Ante resultado incierto pide revisar y no reanuda ciegamente una posible transferencia duplicada.

## Integración pendiente

La app instalada no publica progressActive, progressCompleted, progressPaused, progressError. ../app-integration/progress-state.patch está preparado y comprobado, pero no aplicado a la fuente original ni compilado en las instalaciones.

Para producción hay que corregir el empaquetado/registro del puente antiguo y probar acciones reales. La configuración .qa no debe publicarse como configuración de producción.

## Validación

Ver ../RESULTADO-QA-0.45.3.md. Se separan tests simulados, conexión real y ejecución de acciones. La certificación canary de la aplicación debe registrarse por separado.
