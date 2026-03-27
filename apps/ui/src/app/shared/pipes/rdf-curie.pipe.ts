import { Pipe, PipeTransform } from '@angular/core';
@Pipe({ name: 'rdfCurie', standalone: true })
export class RdfCuriePipe implements PipeTransform {
  transform(iri: string | null): string {
    if (!iri) return '';
    if (iri.startsWith('fibo:') || iri.startsWith('usf:') || iri.startsWith('prov:') || iri.startsWith('doc:')) return iri;
    const pos = Math.max(iri.lastIndexOf('#'), iri.lastIndexOf('/'));
    return pos > -1 ? iri.slice(pos + 1) : iri;
  }
}
