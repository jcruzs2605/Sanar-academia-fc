import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { mensajeError } from '../../../interceptors/error.interceptor';
import { camposFaltantesJugador } from '../../../utils/validaciones';
import { FormsModule } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-crear-jugador',
  standalone: true,
  imports: [FormsModule, RouterLink, CommonModule],
  templateUrl: './crear-jugador.html',
  styleUrl: './crear-jugador.css'
})
export class CrearJugadorComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  isEditing: boolean = false;
  mensajeExito: string = '';
  mensajeError: string = '';

  jugador = {
    nombre: '',
    fecha_nacimiento: '',
    estatura: null,
    peso: null,
    posicion: 'Mediocampista',
    acudiente_id: '',
    categoria_id: ''
  };

  acudientes: any[] = [];
  categorias: any[] = [];

  ngOnInit(): void {
    this.cargarSelects();
  }

  cargarSelects(): void {
    this.http.get<any[]>('/api/admin/acudientes')
      .subscribe({
        next: (data) => this.acudientes = data,
        error: (err) => console.error('Error al cargar acudientes:', err)
      });

    this.http.get<any[]>('/api/admin/categorias')
      .subscribe({
        next: (data) => this.categorias = data,
        error: (err) => console.error('Error al cargar categorías:', err)
      });
  }

  onSubmit(): void {
    this.mensajeExito = '';
    this.mensajeError = '';

    const faltantes = camposFaltantesJugador(this.jugador);
    if (faltantes.length) {
      this.mensajeError = `Faltan campos por completar: ${faltantes.join(', ')}.`;
      return;
    }

    this.http.post('/api/admin/jugadores/nuevo', this.jugador)
      .subscribe({
        next: () => {
          this.mensajeExito = 'Jugador registrado exitosamente';
          this.cdr.detectChanges();
          setTimeout(() => this.router.navigate(['/admin/jugadores']), 1500);
        },
        error: (err) => {
          console.error('Error al crear jugador:', err);
          this.mensajeError = mensajeError(err, 'No se pudo registrar el jugador.');
          this.cdr.detectChanges();
        }
      });
  }
}
