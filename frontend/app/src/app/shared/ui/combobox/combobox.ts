import {
  Component,
  DestroyRef,
  ElementRef,
  inject,
  HostListener,
  computed,
  effect,
  forwardRef,
  untracked,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

/** Opción de un combo filtrable. `hint` se muestra en gris junto a la etiqueta. */
export interface ComboOption {
  value: string;
  label: string;
  hint?: string;
}

let nextId = 0;

/** Quita acentos y mayúsculas para comparar al filtrar ("Méx" encuentra "mexico"). */
function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

/**
 * Select filtrable (autocomplete): se usa igual que un <select> con
 * formControlName, pero permite escribir para filtrar las opciones.
 *
 * Teclado: ↑/↓ recorren, Enter elige, Esc cierra y Tab sale conservando la
 * selección. Si el texto escrito no corresponde a una opción, al salir se
 * restaura la opción seleccionada.
 *
 * El contenedor (host) recibe el borde y el relleno de cada formulario: sus
 * estilos agregan `app-combobox` junto a `select`.
 */
@Component({
  selector: 'app-combobox',
  templateUrl: './combobox.html',
  styleUrl: './combobox.scss',
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => Combobox), multi: true }],
  host: {
    '[class.is-open]': 'open()',
    '[class.is-disabled]': 'isDisabled()',
  },
})
export class Combobox implements ControlValueAccessor {
  readonly options = input<ComboOption[]>([]);
  readonly placeholder = input('Selecciona una opción');
  readonly emptyText = input('Sin coincidencias');
  readonly ariaLabel = input<string | null>(null);
  readonly inputId = input<string | null>(null);
  /** Para formularios nativos (FormData): envía el valor con este nombre. */
  readonly name = input<string | null>(null);
  /**
   * Uso sin formulario (filtros, controles de tabla): valor mostrado. Si el
   * cambio falla, el componente padre puede restaurarlo con writeValue().
   */
  readonly selectedValue = input<string | null | undefined>(undefined);
  /** Uso sin formulario: deshabilita el combo. */
  readonly disabledInput = input(false, { alias: 'disabled' });
  /** Se emite cuando la persona elige una opción (además del cambio del formulario). */
  readonly selected = output<string>();

  private readonly host = viewChild.required<ElementRef<HTMLInputElement>>('field');
  protected readonly listId = `combo-list-${++nextId}`;
  protected readonly value = signal('');
  protected readonly query = signal('');
  protected readonly typing = signal(false);
  protected readonly open = signal(false);
  protected readonly active = signal(0);
  private readonly formDisabled = signal(false);
  protected readonly isDisabled = computed(() => this.formDisabled() || this.disabledInput());
  protected readonly panel = signal<{
    top: number | null;
    bottom: number | null;
    left: number;
    width: number;
    maxHeight: number;
  } | null>(null);

  protected readonly selectedOption = computed(() =>
    this.options().find((option) => option.value === this.value()) ?? null,
  );
  protected readonly filtered = computed(() => {
    const term = normalize(this.typing() ? this.query() : '');
    if (!term) return this.options();
    return this.options().filter((option) =>
      normalize(`${option.label} ${option.hint ?? ''}`).includes(term),
    );
  });
  /** Texto visible: lo que se escribe o, si no, la etiqueta de la opción elegida. */
  protected readonly text = computed(() =>
    this.typing() ? this.query() : (this.selectedOption()?.label ?? ''),
  );

  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  constructor(private readonly element: ElementRef<HTMLElement>) {
    // Captura el scroll de cualquier contenedor (diálogos, paneles), no solo de la ventana.
    const onScroll = (event: Event) => {
      if (!this.open()) return;
      const list = document.getElementById(this.listId);
      if (list && list.contains(event.target as Node)) return; // desplazarse dentro de la lista
      this.place();
    };
    document.addEventListener('scroll', onScroll, true);
    inject(DestroyRef).onDestroy(() => document.removeEventListener('scroll', onScroll, true));

    effect(() => {
      const external = this.selectedValue();
      if (external !== undefined) untracked(() => this.writeValue(external));
    });
    effect(() => {
      if (this.isDisabled()) untracked(() => this.close());
    });
  }

  /** Valor elegido, para leerlo con una referencia de plantilla (#ref.currentValue). */
  get currentValue(): string {
    return this.value();
  }

  // --- ControlValueAccessor ---------------------------------------------------
  writeValue(value: unknown): void {
    this.value.set(value == null ? '' : String(value));
    this.typing.set(false);
  }
  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }
  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }
  setDisabledState(isDisabled: boolean): void {
    this.formDisabled.set(isDisabled);
  }

  // --- Interacción ------------------------------------------------------------
  protected onFocus(event: FocusEvent): void {
    (event.target as HTMLInputElement).select();
  }

  protected onInput(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
    this.typing.set(true);
    this.active.set(0);
    this.openPanel();
  }

  protected toggle(): void {
    if (this.isDisabled()) return;
    if (this.open()) {
      this.close();
      return;
    }
    this.host().nativeElement.focus();
    this.openPanel();
  }

  protected onKeydown(event: KeyboardEvent): void {
    const options = this.filtered();
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        if (!this.open()) this.openPanel();
        else this.move(1, options.length);
        break;
      case 'ArrowUp':
        event.preventDefault();
        if (!this.open()) this.openPanel();
        else this.move(-1, options.length);
        break;
      case 'Enter':
        if (this.open()) {
          event.preventDefault(); // no envía el formulario mientras se elige
          const option = options[this.active()];
          if (option) this.choose(option);
        }
        break;
      case 'Escape':
        if (this.open()) {
          event.preventDefault();
          event.stopPropagation(); // no cierra el diálogo que contiene el combo
          this.close();
        }
        break;
      case 'Tab':
        this.close();
        break;
    }
  }

  protected onBlur(): void {
    this.onTouched();
    // Si el texto escrito coincide exactamente con una opción, se elige.
    if (this.typing()) {
      const exact = this.options().find((option) => normalize(option.label) === normalize(this.query()));
      if (exact) this.choose(exact);
    }
    this.close();
  }

  protected choose(option: ComboOption): void {
    const changed = option.value !== this.value();
    this.value.set(option.value);
    this.close();
    if (changed) {
      this.onChange(option.value);
      this.selected.emit(option.value);
    }
  }

  protected optionId(index: number): string {
    return `${this.listId}-${index}`;
  }

  private move(step: number, total: number): void {
    if (!total) return;
    this.active.set((this.active() + step + total) % total);
    queueMicrotask(() =>
      document.getElementById(this.optionId(this.active()))?.scrollIntoView({ block: 'nearest' }),
    );
  }

  private openPanel(): void {
    if (this.isDisabled()) return;
    if (!this.open()) {
      const index = this.filtered().findIndex((option) => option.value === this.value());
      this.active.set(Math.max(index, 0));
    }
    this.place();
    this.open.set(true);
    queueMicrotask(() =>
      document.getElementById(this.optionId(this.active()))?.scrollIntoView({ block: 'nearest' }),
    );
  }

  private close(): void {
    this.open.set(false);
    this.typing.set(false);
    this.query.set('');
  }

  /** La lista usa position: fixed para no quedar recortada por diálogos o tarjetas. */
  private place(): void {
    const rect = this.element.nativeElement.getBoundingClientRect();
    const below = window.innerHeight - rect.bottom - 12;
    const above = rect.top - 12;
    const openUp = below < 180 && above > below;
    const maxHeight = Math.min(280, Math.max(openUp ? above : below, 120));
    // En campos angostos la lista puede ser más ancha, sin salirse de la pantalla.
    const width = Math.min(Math.max(rect.width, 260), window.innerWidth - 16);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    // Hacia arriba se ancla por el borde inferior, para que una lista corta quede
    // pegada al campo y no a la altura máxima.
    this.panel.set({
      top: openUp ? null : rect.bottom + 4,
      bottom: openUp ? window.innerHeight - rect.top + 4 : null,
      left,
      width,
      maxHeight,
    });
  }

  @HostListener('window:resize')
  protected reposition(): void {
    if (this.open()) this.place();
  }

  @HostListener('document:mousedown', ['$event'])
  protected outside(event: MouseEvent): void {
    if (this.open() && !this.element.nativeElement.contains(event.target as Node)) this.close();
  }
}
