#!/bin/bash
set -e

LSF_TOP_DIR=$(jetpack config lsf.lsf_top)
cat > /etc/systemd/system/lsfd.service <<EOF
[Unit]
Description=IBM Spectrum LSF Daemons
After=network-online.target remote-fs.target
Wants=network-online.target
RequiresMountsFor=/shared

[Service]
Type=forking
Environment="LSF_TOP=${LSF_TOP_DIR}"
ExecStart=/bin/bash -lc 'source \${LSF_TOP}/conf/profile.lsf && lsf_daemons start'
ExecStop=/bin/bash -lc 'source \${LSF_TOP}/conf/profile.lsf && lsf_daemons stop'
ExecReload=/bin/bash -lc 'source \${LSF_TOP}/conf/profile.lsf && lsf_daemons restart'
RemainAfterExit=yes
KillMode=process
Restart=no

[Install]
WantedBy=multi-user.target
EOF

chmod 0644 /etc/systemd/system/lsfd.service
systemctl daemon-reload
systemctl enable lsfd