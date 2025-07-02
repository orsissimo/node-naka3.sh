const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const cors = require('cors');
const Convert = require('ansi-to-html');

const app = express();
const PORT = 3000;
const convert = new Convert();

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

let monitorProcess = null;

app.post('/execute', (req, res) => {
    const { command, type } = req.body;
    
    if (!command || !type) {
        return res.status(400).json({ error: 'Command and type are required' });
    }

    const [cmd, ...args] = command.split(' ');
    
    console.log(`Executing: ${command}`);
    
    res.writeHead(200, {
        'Content-Type': 'text/html',
        'Transfer-Encoding': 'chunked'
    });

    const process = spawn(cmd, args, {
        cwd: __dirname,
        stdio: ['pipe', 'pipe', 'pipe']
    });

    if (type === 'monitor') {
        monitorProcess = process;
    }

    process.stdout.on('data', (data) => {
        const htmlOutput = convert.toHtml(data.toString());
        res.write(htmlOutput);
    });

    process.stderr.on('data', (data) => {
        const htmlOutput = convert.toHtml(data.toString());
        res.write(htmlOutput);
    });

    process.on('close', (code) => {
        res.write(`\nProcess exited with code ${code}\n`);
        res.end();
        
        if (type === 'monitor') {
            monitorProcess = null;
        }
    });

    process.on('error', (error) => {
        res.write(`Error: ${error.message}\n`);
        res.end();
        
        if (type === 'monitor') {
            monitorProcess = null;
        }
    });
});

app.post('/stop-monitor', (req, res) => {
    if (monitorProcess) {
        monitorProcess.kill('SIGTERM');
        monitorProcess = null;
        res.json({ message: 'Monitor process stopped' });
    } else {
        res.json({ message: 'No monitor process running' });
    }
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/advanced', (req, res) => {
    res.sendFile(path.join(__dirname, 'advanced.html'));
});

app.listen(PORT, () => {
    console.log(`Icarus Sandbox server running on http://localhost:${PORT}`);
    console.log('Available scripts:');
    console.log('- create-transaction.sh [miner1|miner2|miner3]');
    console.log('- deploy-contract.sh [miner1|miner2|miner3]');
    console.log('- monitor-chain.sh [miner1|miner2|miner3]');
});