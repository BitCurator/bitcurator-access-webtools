#-*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # Use the precised64 box, change this for 32 bit, or other distro
    config.vm.box = "ubuntu/trusty64"

    # Set the box host-name
    config.vm.hostname = "bca-webtools-0.4.5"

    # Run the provisioning script	
    config.vm.provision :shell, :path => "./provision/bootstrap.sh"

    # Run the server start script	
    config.vm.provision :shell, :path => "./provision/servstart.sh",
     run: "always"

    # Run the Celery daemon start script	
    config.vm.provision :shell, :path => "./provision/taskserv.sh",
     run: "always"

    # Port forward HTTP (80) to host 2020
    config.vm.network :forwarded_port, :host => 8080, :guest => 5000

    config.vm.provider :virtualbox do |vb|
      vb.name = "bca-webtools-0.4.5"
      vb.memory = 2048
      vb.cpus = 1
    end
end
