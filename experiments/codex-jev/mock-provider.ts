// Offline preload: intercepts transport before the upstream helper starts.
const scenario = process.env.JEV_LAB_SCENARIO;
globalThis.fetch = async (input, init) => {
  if (String(input) !== 'https://openrouter.ai/api/alpha/decisions') throw new Error('Wrong provider URL');
  const request = JSON.parse(String(init?.body));
  if (request.model !== 'typesafe/jev-1.13') throw new Error('Wrong model');
  if ((init?.headers as Record<string,string>).authorization !== 'Bearer synthetic-key') throw new Error('Wrong authorization');
  if (scenario === 'network') throw new Error('Synthetic network failure');
  if (scenario === 'malformed') return new Response('{invalid', {status:200});
  if (scenario === 'http-error') return new Response('Synthetic error', {status:401});
  const answers = Object.fromEntries(Object.keys(request.questions).map(name => [name, {noul: scenario === 'invalid-probability' ? -1 : scenario === 'keep-all' || name.endsWith('_t25') ? 1 : 0}]));
  return new Response(JSON.stringify({answers}), {status:200});
};
