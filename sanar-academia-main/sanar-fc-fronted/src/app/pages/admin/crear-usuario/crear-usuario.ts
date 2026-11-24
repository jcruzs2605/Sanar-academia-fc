import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';
import { mensajeError } from '../../../interceptors/error.interceptor';
import { camposVacios } from '../../../utils/validaciones';

@Component({
  selector: 'app-crear-usuario',
  standalone: true,
  imports: [FormsModule, RouterLink, CommonModule],
  templateUrl: './crear-usuario.html',
  styleUrl: './crear-usuario.css'
})
export class CrearUsuarioComponent {
  private http = inject(HttpClient);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  usuario = {
    nombre: '',
    username: '',
    password: '',
    rol: 'profesor'
  };

  mensajeExito: string = '';
  mensajeError: string = '';

  onSubmit(): void {
    this.mensajeExito = '';
    this.mensajeError = '';

    const faltantes = camposVacios(this.usuario, {
      nombre: 'Nombre completo', username: 'Nombre de usuario', password: 'Contraseña', rol: 'Rol'
    });
    if (faltantes.length) {
      this.mensajeError = `Faltan campos por completar: ${faltantes.join(', ')}.`;
      return;
    }
    if (this.usuario.password.length < 6) {
      this.mensajeError = 'La contraseña debe tener al menos 6 caracteres.';
      return;
    }

    this.http.post('/api/admin/usuarios/nuevo', this.usuario)
      .subscribe({
        next: () => {
          this.mensajeExito = '¡Usuario guardado con éxito!';
          this.usuario = { nombre: '', username: '', password: '', rol: 'profesor' };
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.mensajeError = mensajeError(err, 'No se pudo guardar el usuario.');
          this.cdr.detectChanges();
        }
      });
  }
}