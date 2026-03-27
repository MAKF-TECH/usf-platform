import { Pipe, PipeTransform } from '@angular/core';

const PREFIX_MAP: Record<string, string> = {
  'http://www.omg.org/spec/EDMC-FIBO/': 'fibo:',
  'https://spec.edmcouncil.org/fibo/': 'fibo:',
  'http://www.w3.org/ns/prov#': 'prov:',
  'http://www.w3.org/2002/07/owl#': 'owl:',
  'http://www.w3.org/2000/01/rdf-schema#': 'rdfs:',
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf:',
  'https://usf.io/ontology/': 'usf:',
};

@Pipe({ name: 'rdfCurie', standalone: true })
export class RdfCuriePipe implements PipeTransform {
  transform(iri: string | null): string {
    if (!iri) return '';
    for (const [prefix, short] of Object.entries(PREFIX_MAP)) {
      if (iri.startsWith(prefix)) return iri.replace(prefix, short);
    }
    // Try fibo: prefix shorthand
    if (iri.startsWith('fibo:') || iri.startsWith('usf:') || iri.startsWith('prov:')) return iri;
    // Extract local name from URI
    const hash = iri.lastIndexOf('#');
    const slash = iri.lastIndexOf('/');
    const pos = Math.max(hash, slash);
    return pos > -1 ? iri.slice(pos + 1) : iri;
  }
}
