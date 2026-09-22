# Fotos de producto del catalogo de demostracion

Todas las fotos vienen de [Unsplash](https://unsplash.com) y se usan bajo la
[Licencia de Unsplash](https://unsplash.com/license): uso libre, tambien
comercial, sin necesidad de permiso ni atribucion. Se listan igual para poder
rastrear cada imagen. Se bajaron recortadas a 800 x 1000 px desde
`https://images.unsplash.com/photo-<id>`.

`backend/seed_demo.py` las referencia en `prenda.imagen_url` como ruta relativa
(`/img/prendas/<archivo>`), que la web resuelve contra su propio dominio.

| Archivo | Prenda del seed | Foto de Unsplash (id) |
|---|---|---|
| polera-basica-blanca.jpg | Polera basica algodon | 1521572163474-6864f9cf17ab |
| polera-estampada-original.jpg | Polera estampada Original | 1576566588028-4147f3842f27 |
| polera-negra-minimal.jpg | Polera negra minimal | 1618354691373-d851c5c3a990 |
| jean-clasico.jpg | Pantalon jean clasico | 1542272604-787c3835535d |
| jean-skinny-rasgado.jpg | Jean skinny rasgado | 1541099649105-f69ad21f3246 |
| jogger-rosa-palo.jpg | Pantalon jogger rosa palo | 1594633312681-425c7b97ccd1 |
| vestido-floral-rojo.jpg | Vestido floral rojo | 1572804013309-59a88b7e92f1 |
| vestido-largo-gala.jpg | Vestido largo de gala | 1595777457583-95e059d581b8 |
| vestido-blanco-verano.jpg | Vestido blanco de verano | 1515372039744-b8f02a3ae446 |
| chamarra-cuero-negra.jpg | Chamarra de cuero negra | 1551028719-00167b16eac5 |
| chamarra-bomber-terracota.jpg | Chamarra bomber terracota | 1591047139829-d91aecb6caea |
| parka-verde-militar.jpg | Parka verde militar | 1548883354-94bcfe321cbb |
| camisa-denim-estampada.jpg | Camisa denim estampada | 1596755094514-f87e34085b2c |
| camisa-blanca-formal.jpg | Camisa blanca formal | 1598033129183-c4f50c736f10 |
| falda-plisada-negra.jpg | Falda plisada negra | 1583496661160-fb5886a0aaaa |
| falda-midi-beige.jpg | Falda midi beige | 1592301933927-35b597393c0a |

## Imagenes del probador virtual (`*.png`, fondo transparente)

El vestidor virtual de la app movil dibuja la prenda sola sobre el cuerpo, asi
que necesita un PNG con fondo transparente (`asset_ar` tipo `png_overlay`).
La mayoria se obtuvo recortando la foto de Unsplash correspondiente con
[rembg](https://github.com/danielgatis/rembg) (modelos `u2net` y
`u2net_cloth_seg`). Para las fotos donde la prenda no se podia aislar (modelo
de cuerpo entero, prenda parcial) se usaron PNG de
[pngimg.com](https://pngimg.com), uso libre no comercial con atribucion:

| Archivo | Fuente |
|---|---|
| camisa-blanca-formal.png | https://pngimg.com/image/8084 (dress shirt) |
| jean-clasico.png | https://pngimg.com/image/5762 (jeans) |
| jean-skinny-rasgado.png | https://pngimg.com/image/5779 (jeans) |
| vestido-blanco-verano.png | https://pngimg.com/image/82 (dress) |
| vestido-floral-rojo.png | https://pngimg.com/image/147 (dress) |
| vestido-largo-gala.png | https://pngimg.com/image/137 (dress) |
