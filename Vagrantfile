#-*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # Note: The current build requires Ubuntu 17.04.
    config.vm.box = "bento/ubuntu-17.10"

    # Optional "official" cloud xenial box (currently broken):
    #config.vm.box = "https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-vagrant.box"
    # Set the box host-name
    # config.vm.hostname = "ubuntu-xenial"

    # Run the provisioning script
    config.vm.provision :shell, :path => "./provision/bootstrap.sh"

    # Run the server start script
    # config.vm.provision :shell, :path => "./provision/servstart.sh",
    # run: "always"

    # Run the Celery daemon start script
    config.vm.provision :shell, :path => "./provision/taskserv.sh",
     run: "always"

    # Configure synced folder
    # In the example below, the first folder would be located on the host
    # at "/mnt/data", and the shared folder in the VM woud appear at "/vagrant/data"
    # config.vm.synced_folder "/mnt/data", "/vagrant/data"

    # Port forward HTTP (80) to host 2020
    config.vm.network :forwarded_port, :host => 8080, :guest => 80

    config.vm.provider :virtualbox do |vb|
      vb.name = "bca-webtools-0.8.2"
      vb.memory = 4096
      vb.cpus = 2
    end
end
