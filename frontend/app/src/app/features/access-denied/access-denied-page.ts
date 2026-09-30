import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-access-denied-page',
  imports: [RouterLink],
  template: `<section class="state"><span aria-hidden="true">!</span><p>Acceso restringido</p><h1>No tienes permiso para ver esta pantalla</h1><div>Tu sesión es válida, pero tu rol no incluye el permiso necesario. Si consideras que es un error, consulta al administrador de tu empresa.</div><a routerLink="/panel">Volver al inicio</a></section>`,
  styles: [`:host{display:block}.state{max-width:38rem;padding:clamp(2rem,6vw,4rem);margin:5vh auto;background:#fff;border:1px solid var(--flowdesk-border);border-radius:1rem;box-shadow:0 1.5rem 4rem rgb(20 42 56 / 9%);text-align:center}.state>span{display:grid;width:3.2rem;height:3.2rem;place-items:center;margin:0 auto 1rem;color:#fff;background:var(--flowdesk-copper);border-radius:50%;font-weight:900}.state>p{margin:0;color:var(--flowdesk-copper);font-size:.72rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}h1{margin:.6rem 0;color:var(--flowdesk-navy);font-size:clamp(1.8rem,5vw,2.7rem)}.state>div{color:var(--flowdesk-muted);line-height:1.6}.state>a{display:inline-block;padding:.75rem 1rem;margin-top:1.5rem;color:#fff;background:var(--flowdesk-navy);border-radius:.5rem;font-weight:750;text-decoration:none}`]
})
export class AccessDeniedPage {}
