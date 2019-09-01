#//bin/bask
clear
echo "OTA server as service update"

SERVICE=otaserver.service

systemctl stop $SERVICE
systemctl daemon-reload
systemctl enable $SERVICE
systemctl start $SERVICE
systemctl status $SERVICE



