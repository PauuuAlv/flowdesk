import { ComboOption } from '../../shared/ui/combobox/combobox';

/**
 * Monedas con las que trabaja Flowdesk (mismas que backend/app/core/currencies.py).
 * Cada oportunidad, cotización y producto/servicio guarda la suya; por defecto
 * se usa la moneda configurada de la empresa.
 */
export type CurrencyCode = 'MXN' | 'USD';
export const DEFAULT_CURRENCY: CurrencyCode = 'MXN';

export const CURRENCY_OPTIONS: ComboOption[] = [
  { value: 'MXN', label: 'MXN', hint: 'Peso mexicano' },
  { value: 'USD', label: 'USD', hint: 'Dólar estadounidense' },
];

/** Importe de una sola moneda (los totales nunca mezclan monedas). */
export interface MoneyTotal {
  currency: string;
  amount: number;
}

const formatters = new Map<string, Intl.NumberFormat>();

/**
 * "$1,500.00 MXN" / "$20.00 USD". Siempre muestra el código: el símbolo "$" por
 * sí solo es ambiguo y, al traducir la página, se lee como dólares.
 */
export function formatMoney(value: number | string | null | undefined, currency: string | null | undefined, decimals = 2): string {
  const code = currency || DEFAULT_CURRENCY;
  const key = `${code}-${decimals}`;
  let formatter = formatters.get(key);
  if (!formatter) {
    formatter = new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: code,
      currencyDisplay: 'narrowSymbol',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
    formatters.set(key, formatter);
  }
  return `${formatter.format(Number(value ?? 0))} ${code}`;
}

/** Varios totales, uno por moneda: "$100,000.00 MXN · $5,000.00 USD". */
export function formatTotals(totals: MoneyTotal[] | null | undefined, decimals = 2): string {
  if (!totals?.length) return formatMoney(0, DEFAULT_CURRENCY, decimals);
  return totals.map((total) => formatMoney(total.amount, total.currency, decimals)).join(' · ');
}

/** Agrupa importes por moneda (p. ej. el total de una columna del tablero). */
export function sumByCurrency<T>(items: T[], currencyOf: (item: T) => string, amountOf: (item: T) => number): MoneyTotal[] {
  const sums = new Map<string, number>();
  for (const item of items) {
    const currency = currencyOf(item) || DEFAULT_CURRENCY;
    sums.set(currency, (sums.get(currency) ?? 0) + Number(amountOf(item) || 0));
  }
  return [...sums.entries()].map(([currency, amount]) => ({ currency, amount }));
}
