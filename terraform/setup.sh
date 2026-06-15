apt-get update -y

curl -sfL https://get.k3s.io | sh -

mkdir -p /home/ubuntu/.kube

cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown ubuntu:ubuntu /home/ubuntu/.kube/config
chmod 600 /home/ubuntu/.kube/config

echo "export KUBECONFIG=~/.kube/config" >> /home/ubuntu/.bashrc