// set-rec-path.js  (obs-websocket v4 / compat)
// Usage: node set-rec-path.js "<recordPath>" "<profileName?>" "<host?>" "<port?>" "<password?>"

const OBSWebSocket = require('obs-websocket-js');
const obs = new OBSWebSocket();

(async () => {
  const [,, recPathArg, profileArg, hostArg, portArg, passArg] = process.argv;
  if (!recPathArg) {
    console.error('Missing <recordPath>. Usage: node set-rec-path.js "<recordPath>" "<profileName?>" "<host?>" "<port?>" "<password?>"');
    process.exit(2);
  }

  const recordPath = recPathArg;
  const profileName = profileArg || '';        // optional
  const host = hostArg || '127.0.0.1';
  const port = portArg || '4444';
  const password = passArg || '1';

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
