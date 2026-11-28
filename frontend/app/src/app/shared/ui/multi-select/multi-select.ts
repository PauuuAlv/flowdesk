import {
  Component,
  computed,
  ElementRef,
  HostListener,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

import { ComboOption } from '../combobox/combobox';

let nextId = 0;

/** Quita acentos y mayúsculas para comparar al filtrar ("Méx" encuentra "mexico"). */
function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

/**
 * Selección múltiple con casillas para filtros. Sin selección significa "todos".
 *
 * Igual que app-combobox, se escribe directamente en el campo para filtrar
 * las opciones. Cerrado, el campo muestra lo seleccionado.
 *
 * Teclado: escribir filtra; ↑/↓ recorren; Enter marca/desmarca la opción
 * resaltada y limpia lo escrito; Esc cierra; Tab sale. Retroceso con el campo vacío quita la
 * última opción marcada.
 */
@Component({
  selector: 'app-multi-select',
  templateUrl: './multi-select.html',
  styleUrl: './multi-select.scss',
  host: { '[class.is-open]': 'open()' },
})
export class MultiSelect {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly field = viewChild.required<ElementRef<HTMLInputElement>>('field');

  readonly options = input<ComboOption[]>([]);
  /** Valores marcados. */
  readonly selected = input<string[]>([]);
  /** Texto cuando no hay nada marcado (equivale a "todos"). */
  readonly placeholder = input('Todos');
  readonly ariaLabel = input<string | null>(null);
  readonly selectedChange = output<string[]>();

  protected readonly listId = `multi-select-${++nextId}`;
  protected readonly open = signal(false);
  protected readonly query = signal('');
  protected readonly active = signal(0);

  protected readonly selectedSet = computed(() => new Set(this.selected()));
  protected readonly filtered = computed(() => {
    const term = normalize(this.query());
    return term
      ? this.options().filter((option) => normalize(`${option.label} ${option.hint ?? ''}`).includes(term))
      : this.options();
  });
  /** Etiquetas de lo seleccionado, en el orden de las opciones. */
  protected readonly summary = computed(() =>
    this.options()
      .filter((option) => this.selectedSet().has(option.value))
      .map((option) => option.label)
      .join(', '),
  );
  /** Lo que muestra el campo: lo escrito mientras está abierto; si no, la selección. */
  protected readonly text = computed(() => (this.open() ? this.query() : this.summary()));
  protected readonly fieldPlaceholder = computed(() =>
    this.open() ? this.summary() || 'Escribe para filtrar' : this.placeholder(),
  );

  protected openList(): void {
    if (this.open()) return;
    this.query.set('');
    this.active.set(0);
    this.open.set(true);
  }

  protected close(): void {
    this.open.set(false);
    this.query.set('');
  }

  /** Botón de la flecha: abre/cierra y deja el foco en el campo para escribir. */
  protected toggleFromChevron(): void {
    if (this.open()) {
      this.close();
    } else {
      this.openList();
      this.field().nativeElement.focus();
    }
  }

  protected toggleOption(value: string): void {
    const next = new Set(this.selected());
    if (next.has(value)) next.delete(value);
    else next.add(value);
    this.emit(next);
  }

  /** Marca todas las opciones visibles (las que coinciden con lo escrito). */
  protected selectAllVisible(): void {
    this.emit(new Set([...this.selected(), ...this.filtered().map((option) => option.value)]));
  }

  protected clear(): void {
    this.selectedChange.emit([]);
  }

  protected optionId(index: number): string {
    return `${this.listId}-option-${index}`;
  }

  protected onInput(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.active.set(0);
    this.open.set(true);
  }

  protected onKeydown(event: KeyboardEvent): void {
    const count = this.filtered().length;
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        if (!this.open()) this.openList();
        else if (count) this.active.update((i) => (i + 1) % count);
        break;
      case 'ArrowUp':
        event.preventDefault();
        if (this.open() && count) this.active.update((i) => (i - 1 + count) % count);
        break;
      case 'Enter':
        event.preventDefault();
        if (!this.open()) this.openList();
        else if (count) {
          this.toggleOption(this.filtered()[Math.min(this.active(), count - 1)].value);
          // Se limpia lo escrito para buscar la siguiente opción.
          this.query.set('');
          this.active.set(0);
        }
        break;
      case 'Escape':
        if (this.open()) {
          event.preventDefault();
          this.close();
        }
        break;
      case 'Tab':
        this.close();
        break;
      case 'Backspace': {
        // Con el campo vacío, quita la última opción marcada.
        const selected = this.selected();
        if (this.open() && !this.query() && selected.length) {
          event.preventDefault();
          this.emit(new Set(selected.slice(0, -1)));
        }
        break;
      }
    }
  }

  private emit(values: Set<string>): void {
    // Se respeta el orden de las opciones.
    this.selectedChange.emit(this.options().map((o) => o.value).filter((v) => values.has(v)));
  }

  /**
   * Muchos filtros envuelven el campo en un <label>; el navegador reenvía los
   * clics dentro del label a su control. Cancelar la acción por defecto evita
   * ese reenvío (el foco ya lo maneja el campo).
   */
  @HostListener('click', ['$event'])
  protected onHostClick(event: MouseEvent): void {
    event.preventDefault();
  }

  @HostListener('document:mousedown', ['$event'])
  protected onDocumentMousedown(event: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.close();
    }
  }

  @HostListener('focusout', ['$event'])
  protected onFocusOut(event: FocusEvent): void {
    const next = event.relatedTarget as Node | null;
    if (next && !this.host.nativeElement.contains(next)) this.close();
  }
}
