import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

/** Mensaje legible según el estado HTTP cuando el servidor no envía uno propio. */
export function mensajePorEstado(status: number): string {
  switch (status) {
    case 0: return 'No se pudo conectar con el servidor. Verifica tu conexión o que el backend esté en ejecución.';
    case 400: return 'Los datos enviados no son válidos. Revisa el formulario.';
    case 401: return 'Tu sesión expiró o no has iniciado sesión. Vuelve a ingresar.';
    case 403: return 'No tienes permisos para realizar esta acción.';
    case 404: return 'No se encontró la información solicitada. Es posible que haya sido eliminada.';
    case 409: return 'Ya existe un registro con esos datos.';
    default: return status >= 500
      ? 'Ocurrió un error en el servidor. Intenta de nuevo en unos momentos.'
      : 'No se pudo completar la operación.';
  }
}

/** Extrae el mensaje de error de una respuesta HTTP (con respaldo si no hay). */
export function mensajeError(err: any, respaldo?: string): string {
  const delServidor = err?.error?.error;
  if (typeof delServidor === 'string' && delServidor.trim()) return delServidor;
  return respaldo && err?.status !== 0 ? respaldo : mensajePorEstado(err?.status ?? 0);
}

/** Garantiza que toda respuesta de error tenga `error.error` con un mensaje en español. */
export const errorInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const cuerpo = err.error;
      const tieneMensaje = cuerpo && typeof cuerpo === 'object' && typeof cuerpo.error === 'string';
      if (!tieneMensaje) {
        const normalizado = new HttpErrorResponse({
          error: { error: mensajePorEstado(err.status) },
          headers: err.headers,
          status: err.status,
          statusText: err.statusText,
          url: err.url ?? undefined
        });
        return throwError(() => normalizado);
      }
      return throwError(() => err);
    })
  );
