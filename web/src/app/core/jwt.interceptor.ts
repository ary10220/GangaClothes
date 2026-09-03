import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { API_URL } from './api';
import { SesionStore } from './sesion';

/** Agrega el header Authorization a las peticiones dirigidas a nuestra API. */
export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(SesionStore).token;
  if (!token || !req.url.startsWith(API_URL)) return next(req);
  return next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
