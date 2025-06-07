module.exports = {
  apps: [
    {
      name: 'system-x',
      script: '/opt/homebrew/bin/python3.12',
      args: '/Users/francisclase/FinRLX/system_x.py --debug',
      cwd: '/Users/francisclase/FinRLX',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/Users/francisclase/FinRLX',
        SYSTEM_X_MODE: 'autonomous'
      },
      error_file: '/Users/francisclase/FinRLX/logs/system-x-error.log',
      out_file: '/Users/francisclase/FinRLX/logs/system-x-out.log',
      log_file: '/Users/francisclase/FinRLX/logs/system-x-combined.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 30000,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '30s',
      exec_mode: 'fork'
    },
    {
      name: 'system-x-monitor',
      script: '/opt/homebrew/bin/python3.12',
      args: '/Users/francisclase/FinRLX/system_x.py --report',
      cwd: '/Users/francisclase/FinRLX',
      instances: 1,
      autorestart: false,
      watch: false,
      cron_restart: '0 */6 * * *', // Every 6 hours
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/Users/francisclase/FinRLX',
        SYSTEM_X_MODE: 'monitor'
      },
      error_file: '/Users/francisclase/FinRLX/logs/system-x-monitor-error.log',
      out_file: '/Users/francisclase/FinRLX/logs/system-x-monitor-out.log',
      time: true,
      exec_mode: 'fork'
    }
  ],

  deploy: {
    production: {
      user: 'francisclase',
      host: 'localhost',
      ref: 'origin/master',
      repo: 'git@github.com:francisclase/FinRLX.git',
      path: '/Users/francisclase/FinRLX',
      'pre-deploy-local': '',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};