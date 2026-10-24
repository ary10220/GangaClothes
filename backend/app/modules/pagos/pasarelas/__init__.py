"""Pasarelas de pago.

Cada archivo de este paquete habla con UN proveedor y no sabe nada del negocio:
recibe cuanto cobrar y devuelve si se cobro. Quien decide que pasa despues
(comprobante, inventario, bitacora) es `pagos/service.py`.

    cliente_http.py -> HTTPS con autenticacion basica y certificado de cliente
    stripe_gw.py    -> Stripe en modo prueba (tarjeta)
    qr_bcp.py       -> QR del Banco de Credito de Bolivia (OpenBanking)
"""
