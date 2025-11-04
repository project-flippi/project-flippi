// set-rec-path.js  (obs-websocket v4 / compat)
// Usage: node set-rec-path.js "<recordPath>" "<profileName?>" "<host?>" "<port?>" "<password?>"

const fs = require('fs');
const path = require('path');
const OBSWebSocket = require('obs-websocket-js');
const obs = new OBSWebSocket();

function parseArgKv(flag) {
  // parse --keys="C:\path\file.json"
  const m = /^--([^=]+)=(.*)$/.exec(flag || '');
  return m ? { key: m[1], val: m[2] } : null;
}

function loadJsonKeys() {
  // default: %USERPROFILE%\project-flippi\_keys\OBSconnection.json
  const userProfile = process.env.USERPROFILE || process.env.HOME || '';
  const defaultKeys = path.join(userProfile, 'project-flippi', '_keys', 'OBSconnection.json');
  const explicit = process.env.OBS_KEYS; // optional env override

  // allow CLI --keys=...
  const kv = process.argv.slice(2).map(parseArgKv).find(Boolean);
  const cliKeys = kv && kv.key.toLowerCase() === 'keys' ? kv.val : null;

  const candidate = cliKeys || explicit || defaultKeys;

  if (!fs.existsSync(candidate)) {
    throw new Error(`OBS keys file not found at: ${candidate}`);
  }
  let cfgRaw;
  try {
    cfgRaw = fs.readFileSync(candidate, 'utf8');
  } catch (e) {
    throw new Error(`Could not read keys file: ${candidate} (${e.message})`);
  }
  let cfg;
  try {
    cfg = JSON.parse(cfgRaw);
  } catch (e) {
    throw new Error(`Keys file is not valid JSON: ${candidate} (${e.message})`);
  }


  const host = (cfg.OBS_HOST ?? '').toString().trim();
  const port = (cfg.OBS_PORT ?? '').toString().trim();
  const password = (cfg.OBS_PASSWORD ?? '').toString();

  if (!host) throw new Error('OBS_HOST missing/empty in keys JSON');
  if (!port) throw new Error('OBS_PORT missing/empty in keys JSON');
  if (!password && password !== '') {
    // allow empty string password, but disallow undefined
    throw new Error('OBS_PASSWORD missing in keys JSON');
  }
  return { host, port, password, keysPath: candidate };
}

(async () => {
  const [,, recPathArg, profileArg, hostArg, portArg, passArg] = process.argv;
  if (!recPathArg) {
    console.error('Missing <recordPath>. Usage: node set-rec-path.js "<recordPath>" "<profileName?>" "<host?>" "<port?>" "<password?>"');
    process.exit(2);
  }

  const recordPath = recPathArg;
  const profileName = profileArg ;        // optional
  
  // Load from JSON first, then let CLI values override if provided.
  let jsonKeys = { host: '', port: '', password: '', keysPath: '' };
  try {
    jsonKeys = loadJsonKeys();
  } catch (e) {
    console.error('[ERROR] ' + e.message);
    console.error('Tip: create %USERPROFILE%\\project-flippi\\_keys\\OBSconnection.json like:');
    console.error('{ "OBS_HOST": "127.0.0.1", "OBS_PORT": "4444", "OBS_PASSWORD": "1" }');
    process.exit(1);
  }

  const host = (hostArg && !hostArg.startsWith('--')) ? hostArg : jsonKeys.host;
  const port = (portArg && !portArg.startsWith('--')) ? portArg : jsonKeys.port;
  const password = (passArg && !passArg.startsWith('--')) ? passArg : jsonKeys.password;
  
  if (!host || !port) {
    console.error('[ERROR] Host/port not resolved. Check your JSON or CLI args.');
    process.exit(1);
  }

  try {
    await obs.connect({ address: `${host}:${port}`, password });

    
    if (profileName) {
      await obs.send('SetCurrentProfile', { 'profile-name': profileName });
    }

    // Set path (compat-safe)
    await obs.send('SetRecordingFolder', { 'rec-folder': recordPath });
    const got = await obs.send('GetRecordingFolder');
    console.log('Recording path set via SetRecordingFolder');
    console.log(' rec-folder =', got['rec-folder']);

    // Start Replay Buffer if not running
    try {
      const r = await obs.send('GetReplayBufferStatus');
      if (!r['isReplayBufferActive']) {
        console.log('Replay Buffer not active, starting…');
        await obs.send('StartReplayBuffer');
      } else {
        console.log('Replay Buffer already active.');
      }
    } catch (e) {
      // If Replay Buffer is disabled in OBS settings, this may throw
      console.log('Could not query/start Replay Buffer (is it enabled in OBS Settings > Output?)', e?.message || e);
    }

    obs.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('Failed to set recording path via obs-websocket (v4):', err?.message || err);
    try { obs.disconnect(); } catch {}
    process.exit(1);
  }
})();
