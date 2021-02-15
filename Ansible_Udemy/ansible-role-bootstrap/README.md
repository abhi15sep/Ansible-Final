[![Build Status](https://travis-ci.org/abdennour/ansible-role-bootstrap.svg?branch=master)](https://travis-ci.org/abdennour/ansible-role-bootstrap)

abdennnour.bootstrap
=========

Bootstrap Passwordless SSH User
This is useful for the communication between the control node and the target host(s)

```sh
ansible-galaxy install abdennour.bootstrap
```

Requirements
------------

The below requirements are needed on the host that executes this role:

- ssh-keygen


Role Variables
--------------


| Variable                | Description                                        | Default / Choices                               |
| ----------------------- | -----------------------------------------------    | ----------------------------------------------- |
| `bootstrap_username`    | name of the new user                               | (string) `ansible`                              |
| `bootstrap_keyair_path` | [path of SSH private keyp][1]                      | (string) `/tmp/{{ bootstrap_username }}_id_rsa` |
| `bootstrap_keyair_type` | [algorithm used to generate the SSH private key][2]| (string) `rsa`                                  |
| `bootstrap_keyair_size` | [number of bits in the private key to create][3]   | (int) `4096`                                    |
| `bootstrap_backup.type` | Type of Backing up the private key of the new user | (string) `debug`                                |


Dependencies
------------

ssh-keygen 

Example Playbook
----------------

This is how you can use it:

    - hosts: all
      roles:
         - role: abdennour.bootstrap
           bootstrap_username: ansible
          

License
-------

BSD


[1]: https://docs.ansible.com/ansible/latest/modules/openssh_keypair_module.html#parameter-path
[2]: https://docs.ansible.com/ansible/latest/modules/openssh_keypair_module.html#parameter-type
[3]: https://docs.ansible.com/ansible/latest/modules/openssh_keypair_module.html#parameter-size