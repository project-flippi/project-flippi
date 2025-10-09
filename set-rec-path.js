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
  const password = passArg || '';

  try {
    await obs.connect({ address: `${host}:${port}`, password });

    // Log server version so we know what we’re talking to
    try {
      const ver = await obs.send('GetVersion');
      console.log('Connected to obs-websocket v4 server:', ver);
    } catch (e) {
      console.log('Connected (GetVersion not available)', e && e.message);
    }

    // Ensure we set params on the intended profile
    if (profileName) {
      await obs.send('SetCurrentProfile', { 'profile-name': profileName });
    }

    // Try SetProfileParameter first (if server supports it)
    async function trySetProfileParameter() {
      await obs.send('SetProfileParameter', {
        category: 'SimpleOutput',
        parameter: 'FilePath',
        value: recordPath
      });
      await obs.send('SetProfileParameter', {
        category: 'AdvOut',
        parameter: 'RecFilePath',
        value: recordPath
      });

      const simple = await obs.send('GetProfileParameter', {
        category: 'SimpleOutput',
        parameter: 'FilePath'
      });
      const adv = await obs.send('GetProfileParameter', {
        category: 'AdvOut',
        parameter: 'RecFilePath'
      });

      console.log('Recording path set via SetProfileParameter');
      console.log(' SimpleOutput.FilePath =', simple.value);
      console.log(' AdvOut.RecFilePath   =', adv.value);
    }

    // Fallback: v4’s SetRecordingFolder (works across modes on v4)
    async function trySetRecordingFolder() {
      await obs.send('SetRecordingFolder', { 'rec-folder': recordPath });
      const got = await obs.send('GetRecordingFolder');
      console.log('Recording path set via SetRecordingFolder');
      console.log(' rec-folder =', got['rec-folder']);
    }

    try {
      await trySetProfileParameter();
    } catch (e) {
      const msg = (e && e.error) || (e && e.message) || String(e);
      if (/invalid request type/i.test(msg) || /Unknown request/i.test(msg)) {
        console.log('SetProfileParameter not supported on this server. Falling back to SetRecordingFolder…');
        await trySetRecordingFolder();
      } else {
        throw e;
      }
    }

    obs.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('Failed to set recording path via obs-websocket (v4):', err && err.message ? err.message : err);
    try { obs.disconnect(); } catch {}
    process.exit(1);
  }
})();
