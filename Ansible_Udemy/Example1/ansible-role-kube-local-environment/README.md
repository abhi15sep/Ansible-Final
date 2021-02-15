Role Name
=========

Consolidator of roles relevant to Kubernetes local env

Requirements
------------

no prereeuisites

Role Variables
--------------

Same Variables of dependent roles (check : meta/main.yml)

Dependencies
------------

It is already a consolidator of other roles.

- andrewrothstein.kubectl
- andrewrothstein.kubernetes-helm
- abdennour.helmfile
- samcre.aws_iam_authenticator

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: localhost
      roles:
         - abdennour.kube_local_environment

License
-------

MIT

Author Information
------------------

Abdennour TOUMI <http://kubernetes.tn>
