#-*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # Note: The current build is tested only with Ubuntu 18.04.
    config.vm.box = "bento/ubuntu-18.04"

    # Run the provisioning script. This installs packages and builds sources.
    # Runs only on the first instance of "vagrant up".
    config.vm.provision :shell, :path => "./provision/bootstrap.sh"

    # Run the Celery daemon start script. This starts the server.
    # Runs on each execution of "vagrant up".
    config.vm.provision :shell, :path => "./provision/taskserv.sh",
     run: "always"

    # Configure synced folder
    # In the example below, the first folder would be located on the host
    # at "/mnt/data", and the shared folder in the VM woud appear at "/vagrant/data"
    # config.vm.synced_folder "/mnt/data", "/vagrant/data"
    config.vm.synced_folder "./disk-images", "/var/bcaw/disk-images", owner: "www-data", group: "www-data", mount_options: ["ro","dmode=0755", "fmode=0444"]

    # Port forward HTTP (80) to host 2020
    config.vm.network :forwarded_port, :host => 8080, :guest => 80

    config.vm.provider :virtualbox do |vb|
      vb.name = "bca-webtools-0.9.21"
      vb.memory = 4096
      vb.cpus = 2
    end
end
