import {
  Component,
  computed,
  ElementRef,
  HostListener,
  inject,
  input,
  output,
  signal,
} from '@angular/core';

import { ComboOption } from '../combobox/combobox';

let nextId = 0;

/** Quita acentos y mayúsculas para comparar al filtrar. */
function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

/**
 * Selección múltiple con casillas. Sin selección significa "todos".
 *
 * Teclado: Enter/Espacio/↓ abren; ↑/↓ recorren; Espacio o Enter marcan;
 * Esc cierra. Con muchas opciones muestra un buscador.
 */
@Component({
  selector: 'app-multi-select',
  templateUrl: './multi-select.html',
  styleUrl: './multi-select.scss',
  host: { '[class.is-open]': 'open()' },
})
export class MultiSelect {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly options = input<ComboOption[]>([]);
  /** Valores marcados. */
  readonly selected = input<string[]>([]);
  /** Texto cuando no hay nada marcado (equivale a "todos"). */
  readonly placeholder = input('Todos');
  readonly ariaLabel = input<string | null>(null);
  /** A partir de cuántas opciones se muestra el buscador. */
  readonly searchFrom = input(7);
  readonly selectedChange = output<string[]>();

  protected readonly listId = `multi-select-${++nextId}`;
  protected readonly open = signal(false);
  protected readonly query = signal('');
  protected readonly active = signal(0);

  protected readonly selectedSet = computed(() => new Set(this.selected()));
  protected readonly filtered = computed(() => {
    const term = normalize(this.query());
    return term
      ? this.options().filter((option) => normalize(option.label).includes(term))
      : this.options();
  });
  protected readonly summary = computed(() => {
    const chosen = this.options().filter((option) => this.selectedSet().has(option.value));
    if (chosen.length === 0) return this.placeholder();
    // Con varias, se listan (el contador al lado indica cuántas son).
    return chosen.map((option) => option.label).join(', ');
  });
  protected readonly summaryTitle = computed(() =>
    this.options()
      .filter((option) => this.selectedSet().has(option.value))
      .map((option) => option.label)
      .join(', '),
  );

  protected toggleOpen(): void {
    this.open.update((value) => !value);
    if (this.open()) {
      this.query.set('');
      this.active.set(0);
    }
  }

  protected toggleOption(value: string): void {
    const next = new Set(this.selected());
    if (next.has(value)) next.delete(value);
    else next.add(value);
    // Se respeta el orden de las opciones.
    this.selectedChange.emit(this.options().map((o) => o.value).filter((v) => next.has(v)));
  }

  protected selectAllVisible(): void {
    const next = new Set([...this.selected(), ...this.filtered().map((option) => option.value)]);
    this.selectedChange.emit(this.options().map((o) => o.value).filter((v) => next.has(v)));
  }

  protected clear(): void {
    this.selectedChange.emit([]);
  }

  protected optionId(index: number): string {
    return `${this.listId}-option-${index}`;
  }

  protected onTriggerKeydown(event: KeyboardEvent): void {
    if (['Enter', ' ', 'ArrowDown'].includes(event.key) && !this.open()) {
      event.preventDefault();
      this.toggleOpen();
      return;
    }
    this.onListKeydown(event);
  }

  protected onListKeydown(event: KeyboardEvent): void {
    if (!this.open()) return;
    const count = this.filtered().length;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.open.set(false);
    } else if (event.key === 'ArrowDown' && count) {
      event.preventDefault();
      this.active.update((i) => (i + 1) % count);
    } else if (event.key === 'ArrowUp' && count) {
      event.preventDefault();
      this.active.update((i) => (i - 1 + count) % count);
    } else if ((event.key === 'Enter' || (event.key === ' ' && event.target instanceof HTMLButtonElement)) && count) {
      event.preventDefault();
      this.toggleOption(this.filtered()[this.active()].value);
    }
  }

  protected onSearch(value: string): void {
    this.query.set(value);
    this.active.set(0);
  }

  @HostListener('document:mousedown', ['$event'])
  protected onDocumentMousedown(event: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.open.set(false);
    }
  }

  @HostListener('focusout', ['$event'])
  protected onFocusOut(event: FocusEvent): void {
    const next = event.relatedTarget as Node | null;
    if (next && !this.host.nativeElement.contains(next)) this.open.set(false);
  }
}
