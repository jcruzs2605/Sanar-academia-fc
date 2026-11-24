/** Devuelve las etiquetas de los campos vacíos, según un mapa {campo: etiqueta}. */
export function camposVacios(datos: Record<string, any>, etiquetas: Record<string, string>): string[] {
  return Object.entries(etiquetas)
    .filter(([campo]) => {
      const v = datos[campo];
      return v === null || v === undefined || (typeof v === 'string' && !v.trim()) || (Array.isArray(v) && !v.length);
    })
    .map(([, etiqueta]) => etiqueta);
}

export function camposFaltantesJugador(j: any): string[] {
  return camposVacios(j, {
    nombre: 'Nombre del jugador',
    fecha_nacimiento: 'Fecha de nacimiento',
    estatura: 'Estatura',
    peso: 'Peso',
    posicion: 'Posición',
    acudiente_id: 'Acudiente',
    categoria_id: 'Categoría'
  });
}
