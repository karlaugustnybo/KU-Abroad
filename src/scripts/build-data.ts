import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Dataset, Institution, AgreementRow, ExchangeQuery } from '../src/lib/types';
import { aggregateGradeRequirement, encodeGradeRequirement } from '../src/lib/grade';
import { PORTAL_URL, summarize } from '../src/lib/exchange';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const DATA = resolve(ROOT, 'data');
const OUTPUT = fileURLToPath(new URL('../src/assets/data/institutions.json', import.meta.url));
const INDEX_OUTPUT = fileURLToPath(new URL('../src/assets/data/explorer-index.json', import.meta.url));
const DETAILS_OUTPUT = fileURLToPath(new URL('../src/assets/data/institution-details.json', import.meta.url));
const COORDINATE_OVERRIDES = resolve(ROOT, 'scripts/geocode_overrides.json');
const readJson = async <T>(path: string): Promise<T> => JSON.parse(await readFile(path, 'utf8'));
const EXCLUDED_INSTITUTION_CODES = new Set(['DA-Overflytning']);

interface RunState {
  schemaVersion: number;
  runId: string;
  completedAt: string;
  academicYears: string[];
  studyFields: string[];
  institutions: Record<string, Omit<Institution, 'agreements'>>;
  agreements: Record<string, AgreementRow & { id: string; institutionId: string }>;
  queries: Record<string, ExchangeQuery>;
}
export function buildFromRun(
  state: RunState,
  previous: Dataset,
  coordinateOverrides: Record<string, { lat: number; lon: number }> = {},
): Dataset {
  if (![1, 2].includes(state.schemaVersion) || !state.completedAt) throw Error('Run is not complete');
  const expected = state.academicYears.length * (state.studyFields.length + 1);
  if (!expected || Object.keys(state.queries).length !== expected) throw Error('Incomplete query coverage');
  const sourceInstitutions = Object.values(state.institutions).filter(institution =>
    !EXCLUDED_INSTITUTION_CODES.has(institution.partnerDetails?.code ?? ''),
  );
  const knownInstitutions = new Set(sourceInstitutions.map(institution => institution.id));
  for (const year of state.academicYears) {
    for (const field of [null, ...state.studyFields]) {
      const query = state.queries[`${year}|${field ?? '*'}`];
      if (!query || query.status !== 'success' || query.academicYear !== year || query.studyField !== field || !query.collectedAt) throw Error('Missing successful query');
      const seen = new Set<string>();
      for (const match of query.matches) {
        if (seen.has(match.institutionId) || !knownInstitutions.has(match.institutionId)) throw Error('Duplicate or unknown institution');
        seen.add(match.institutionId);
        if (!match.agreementIds.length || new Set(match.agreementIds).size !== match.agreementIds.length) throw Error('Empty or duplicate agreement relation');
        for (const id of match.agreementIds) {
          const agreement = state.agreements[id];
          if (!agreement || agreement.institutionId !== match.institutionId || !agreement.details?.['Academic year']?.includes(year)) throw Error('Invalid agreement relation');
        }
      }
    }
  }
  // Reuse coordinates only for an unambiguous exact name/country/city match.
  const identity = (i: Pick<Institution,'name'|'country'|'city'>) => JSON.stringify([i.name,i.country,i.city].map(v=>v.normalize('NFKC').toLowerCase().trim()));
  const oldByIdentity = new Map<string, Institution[]>();
  for (const institution of previous.institutions) {
    const id = identity(institution);
    oldByIdentity.set(id, [...(oldByIdentity.get(id) ?? []), institution]);
  }
  const institutions = sourceInstitutions.map(institution => {
    const old = oldByIdentity.get(identity(institution));
    const agreements = Object.values(state.agreements).filter(a=>a.institutionId===institution.id).map(a=>({...a, portalUrl:PORTAL_URL, detailToken:null}));
    const manual = coordinateOverrides[institution.name];
    const coordinates = manual ?? (old?.length === 1 ? { lat:old[0].lat, lon:old[0].lon } : {});
    return { ...institution, ...coordinates, agreements, agreementCount:agreements.length };
  });
  return {
    institutions, stats:summarize(institutions), generatedAt:state.completedAt,
    exchange: { runId:state.runId, academicYears:state.academicYears, studyFields:state.studyFields,
      collectedAt:state.completedAt, sourceUrl:PORTAL_URL,
      coverage:{ expectedQueries:expected, successfulQueries:expected, status:'complete' },
      queries:Object.values(state.queries) },
  };
}

async function main() {
  const previousText = await readFile(OUTPUT, 'utf8');
  const previous: Dataset = JSON.parse(previousText);
  const pointerPath = resolve(DATA, 'current_portal_run.json');
  let dataset: Dataset;
  if (existsSync(pointerPath)) {
    const pointer = await readJson<{runId:string}>(pointerPath);
    if (!/^[a-zA-Z0-9._-]+$/.test(pointer.runId)) throw Error('Invalid run ID');
    const dir = resolve(DATA, 'portal-runs', pointer.runId);
    const proof = await readJson<{status:string}>(resolve(dir,'verification.json'));
    const quality = await readJson<{status:string}>(resolve(dir,'quality-report.json'));
    if (proof.status !== 'passed' || quality.status !== 'complete') throw Error('Run has not passed validation; keeping previous dataset');
    const coordinateOverrides = await readJson<Record<string, {lat:number;lon:number}>>(COORDINATE_OVERRIDES);
    dataset = buildFromRun(await readJson<RunState>(resolve(dir,'state.json')), previous, coordinateOverrides);
  } else {
    dataset = previous;
    const catalogPath = resolve(DATA,'portal_catalog.json');
    if (existsSync(catalogPath) && !previous.exchange?.coverage.successfulQueries) {
      const catalog = await readJson<{academicYears:string[];studyFields:string[]}>(catalogPath);
      dataset = { ...previous, exchange: { ...catalog, runId:'unverified', collectedAt:previous.generatedAt, sourceUrl:PORTAL_URL,
        coverage:{expectedQueries:catalog.academicYears.length*(catalog.studyFields.length+1),successfulQueries:0,status:'incomplete'}, queries:[] } };
    }
    console.log('No fully validated portal run. Retaining the historical overview; no study-field matches published.');
  }
  // Never replace the only copy of historical data. Preserve the exact previous bytes.
  const history = resolve(DATA,'dataset-history');
  await mkdir(history,{recursive:true});
  const hash = createHash('sha256').update(previousText).digest('hex');
  const backup = resolve(history,`${hash}.json`);
  if (!existsSync(backup)) await writeFile(backup,previousText,{flag:'wx'});
  const next = JSON.stringify(dataset);
  await writeFile(`${OUTPUT}.tmp`,next);
  await rename(`${OUTPUT}.tmp`,OUTPUT);
  const institutionIndexes = new Map(dataset.institutions.map((institution, index) => [institution.id, index]));
  const agreementIds = dataset.institutions.flatMap(institution => institution.agreements.map(agreement => agreement.id));
  const agreementIndexes = new Map(agreementIds.map((id, index) => [id, index]));
  const agreementDetailsById = new Map(dataset.institutions.flatMap(institution => institution.agreements.map(agreement => [agreement.id, agreement.details] as const)));
  const gradeRequirements = agreementIds.map(id => encodeGradeRequirement(aggregateGradeRequirement(agreementDetailsById.get(id))));
  const agreementPrograms = agreementIds.map(id => agreementDetailsById.get(id)?.['Name of program']?.trim() ?? '');
  const agreementPlaces = agreementIds.map(id => {
    const places = Number.parseInt(agreementDetailsById.get(id)?.['Total number'] ?? '', 10);
    return Number.isFinite(places) ? places : -1;
  });
  const agreementStudyLevels = agreementIds.map(id => {
    const details = agreementDetailsById.get(id);
    return (details?.Bachelor === 'Yes' ? 1 : 0)
      | (details?.['Second cycle/Master/Postgraduate'] === 'Yes' ? 2 : 0)
      | (details?.['Third cycle/Phd/Doctoral'] === 'Yes' ? 4 : 0);
  });
  const agreementFeatures = agreementIds.map(id => {
    const details = agreementDetailsById.get(id);
    return (details?.['Accepted proof of language proficiency (required AFTER nomination)']?.trim() ? 1 : 0)
      | (details?.['Language requirements']?.trim() ? 1 : 0)
      | (details?.Housing?.trim() ? 2 : 0)
      | (details?.Scholarships?.trim() ? 4 : 0);
  });
  const version = dataset.exchange?.runId ?? dataset.generatedAt;
  const index = {
    version,
    generatedAt: dataset.generatedAt,
    sourceUrl: dataset.exchange?.sourceUrl ?? PORTAL_URL,
    coverage: dataset.exchange?.coverage ?? { expectedQueries: 0, successfulQueries: 0, status: 'incomplete' as const },
    academicYears: dataset.exchange?.academicYears ?? [],
    studyFields: dataset.exchange?.studyFields ?? [],
    programs: [...new Set(agreementPrograms.filter(Boolean))].sort(),
    studyLevels: ([['bachelor', 1], ['master', 2], ['doctoral', 4]] as const).filter(([, bit]) => agreementStudyLevels.some(value => value & bit)).map(([level]) => level),
    agreementIds,
    gradeRequirements,
    agreementPrograms,
    agreementPlaces,
    agreementStudyLevels,
    agreementFeatures,
    institutions: dataset.institutions.map(({ agreements, partnerDetails: _partnerDetails, eventCount: _eventCount, ...institution }) => ({
      ...institution,
      agreementIds: agreements.map(agreement => agreementIndexes.get(agreement.id)!),
    })),
    queries: (dataset.exchange?.queries ?? []).map(query => ({
      academicYear: query.academicYear,
      studyField: query.studyField,
      status: query.status,
      collectedAt: query.collectedAt,
      matches: query.matches.map(match => [institutionIndexes.get(match.institutionId)!, match.agreementIds.map(id => agreementIndexes.get(id)!)]),
    })),
  };
  const detailRecords = Object.fromEntries(dataset.institutions.map(institution => [institution.id, { ...institution, datasetVersion: version }]));
  await Promise.all([
    writeFile(`${INDEX_OUTPUT}.tmp`, JSON.stringify(index)),
    writeFile(`${DETAILS_OUTPUT}.tmp`, JSON.stringify(detailRecords)),
  ]);
  await rename(`${INDEX_OUTPUT}.tmp`, INDEX_OUTPUT);
  await rename(`${DETAILS_OUTPUT}.tmp`, DETAILS_OUTPUT);
  console.log(`Built ${dataset.institutions.length} institutions; ${dataset.exchange?.coverage.successfulQueries ?? 0} verified queries.`);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error=>{console.error(error);process.exitCode=1;});
}
