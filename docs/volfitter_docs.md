# volfitter

In this document I provide an overview of the volfitter application. The first section
discusses the architecture and design of the system; the second section describes the
logic and available functionality; and finally, the third section discusses possible
extensions and how they would fit into the design.

## Architecture and Design

This section describes the architecture and design of the volfitter application, discussing
approaches and design choices that were taken along the way.

At a high level, the design of the system follows the 
[hexagonal architecture](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)), 
or ports and adapters, pattern. This pattern describes a design with a central application
core which is isolated from the environment in which it runs; the application core communicates
with the outside world via ports and adapters, which will be discussed in more detail below.

The application core consists of a [domain layer](https://en.wikipedia.org/wiki/Domain_model) 
containing the business logic (everything to do with options and vol fitting) and a service 
layer which orchestrates the functionality provided by the domain model.

Conceptually, the service layer expresses _what_ the application does (e.g., fit a full
surface from raw market IVs and validate the output), and the domain model expresses _how_
this is done. The service and domain layers are both written in language that is intelligible
to business domain experts (traders and quants). The adapters, meanwhile, contain all the
code related to databases and filesystems and networks and everything else that connects
the application to the outside world.

Driving all this are one or more entry points: An entry point is a thin layer that does
little more than boot up the system. Currently I supply just a single entry point, `volfitter.py`,
which is exposed as a command-line script when the volfitter is installed. It does nothing
more than gather the application configuration, create the service layer and plug in the 
adapters that are configured by the user, and start a timer which repeatedly triggers the service layer.

The package structure of the volfitter application is shown below. I'll now walk through
each of the important pieces in more detail; I will cover the various pieces in order of
the conceptual flow of logic, which differs from the (alphabetical) order in which they are
displayed in the package structure.

```
src
└── volfitter
    ├── adapters
    │   ├── current_time_supplier.py
    │   ├── final_iv_consumer.py
    │   ├── forward_curve_supplier.py
    │   ├── option_metrics_helpers.py
    │   ├── pricing_supplier.py
    │   ├── raw_iv_supplier.py
    │   └── sample_data_loader.py
    ├── domain
    │   ├── datamodel.py
    │   ├── final_iv_validation.py
    │   ├── fitter.py
    │   └── raw_iv_filtering.py
    ├── entrypoints
    │   └── volfitter.py
    ├── service_layer
    │   └── service.py
    ├── composition_root.py
    └── config.py
```

### Entry Points

An entry point is a thin layer that boots up the application. When the volfitter package
is installed, the entrypoint in `volfitter.py` is exposed as a command-line script. It does
the following (in addition to basic tasks like setting up logging):

- Load user configuration (see below).
- Ask the composition root (see below) to create the service layer and the configured adapters based on the user configuration.
- Create and start a timer which repeatedly triggers the service layer logic on an interval.

A UML diagram of the entry point's responsibilities is included below (`apschedulers` is
the third-party scheduler library I use for the timer):

![entrypoints_uml](../img/entrypoints_uml.png)

### Configuration

The volfitter makes use of [environ-config](https://environ-config.readthedocs.io/en/stable/index.html)
for user configuration. The user parameters are set via environment variables. When the application
starts, a `VolfitterConfig` object is created from any parameter values that are found in the
process's environment variables; default values are used for any parameters that are not set.

Among the benefits of this approach are:

1. Configuration is encapsulated in a single object, `VolfitterConfig` (with subclasses for specific pieces of the application), which can be passed around where needed, preventing configuration code from being scattered throughout the codebase.
2. Setting parameters via environment variables makes deployment and running the application in different environments easy.
3. For use in tests, `environ-config` provides a light-weight way to create configuration objects from hard-coded values rather than reading from the environment.

The configuration lives in `config.py`. The specific user parameters that are available will be described in the "Logic and Functionality" section of this document.

### Dependency Injection and the Composition Root

The application is written with the principles of dependency inversion and dependency injection (DI)
in mind. Classes depend on abstract base classes rather than concrete implementations ("depend on abstractions, not
on concretions") and dependency injection is performed via the constructors. This ensures the
application is modular and that different implementations of various components can easily be swapped out.

For example, although I have implemented the SVI volatility model, switching to a different
model would be as easy as providing a different implementation of `AbstractSurfaceFitter`.
The implementation could be selected at runtime based on user configuration. Similarly,
I provide adapters to run the application on sample data, but it could easily be run live
or in backtest mode by providing different implementations of the I/O abstract base classes
and selecting the desired implementation at startup. In particular, the user can set the
parameter `VOLFITTER_VOLFITTER_MODE` to control whether the volfitter runs on sample data,
or live, or in backtest mode, etc. Currently only the sample data mode is implemented,
but this parameter is exposed to demonstrate how easy it would be to support additional modes.

The actual instantiation of the objects and the wiring together of the dependency graph is
done in `composition_root.py`, named after the
[composition root](https://stackoverflow.com/questions/6277771/what-is-a-composition-root-in-the-context-of-dependency-injection) 
pattern. As this is a simple application, I perform dependency injection by hand rather than
using a framework (also because dependency injection is not as common in the Python world as
it is in some other languages, so while DI frameworks for Python do exist, they are not
necessarily commonplace.)

### Service Layer

The service layer, together with the domain model, makes up the application core in our
hexagonal architecture. Conceptually, the service layer defines the use cases of the system:
It is "orchestation code" that uses the functionality provided by the domain model to perform
a particular task, while getting input from and sending output to the ports and adapters that
surround the application core.

In the volfitter, there is currently only a single use case, and thus only one method on the
service layer: `fit_full_surface`. Adding additional use cases or paths through the system,
such as a path to fit single market events rather than fitting the full surface, could be
achieved by adding new methods to the service layer that use the domain model in different ways.
This will be explored further in the "Discussion of Possible Extensions" section of this
document.

A UML diagram of `VolfitterService` is shown below. Some of its dependencies are ports
for input and output, and some dependencies are domain classes for carrying out business logic.
All dependencies are abstract so that the application can easily be run with different setups.

![service_layer_uml](../img/service_layer_uml.png)

### Domain Model

The `domain` package contains the application's 
[domain model](https://en.wikipedia.org/wiki/Domain_model). Together with the service layer, 
the domain layer makes up the central application core. Following the principles of
[domain-driven design](https://en.wikipedia.org/wiki/Domain-driven_design), the domain
layer contains the business logic of the application. Conceptually, the language, requirements,
and functionality of the domain layer should be intelligible to business domain 
experts&mdash;in our case, traders and quants.

It contains both data, which I
put in the `datamodel` package, and behavior, which lives in the other sub-packages within
the domain layer.

I will discuss the available functionality in the "Logic and Functionality" section, so
here I focus on the class hierarchy and dependency structure.

The volfitter must perform filtering of the raw IVs before passing them to the fitter. The
raw IV filters are shown in the below UML diagram. Although all currently available
filters are `AbstractPerExpiryRawIVFilter`s, they do not need to be: We could add a filter
that operates across all expiries, for example one that computes a wide market threshold
based on a global rather than per-expiry median.

The `CompositeRawIVFilter` is always the filter implementation which which the `VolfitterService`
is constructed: It contains an arbitrary number of other filters and applies them each in
turn, making the addition of new filters or the use of a subset of them extremely easy.

![raw_iv_filtering_uml](../img/raw_iv_filtering_uml.png)

The below UML diagram shows the vol surface fitters themselves. At present I have implemented
one main fitter, for the SVI model. However I also provide a toy `MidMarketSurfaceFitter`,
mainly to show how easy it would be to swap out the surface model. The choice of `SVISurfaceFitter`
or `MidMarketSurfaceFitter` can be controled by the user via the `VOLFITTER_SURFACE_MODEL` parameter.

The `SVISurfaceFitter` has a calibrator, which itself can be swapped out via the
`VOLFITTER_SVI_CONFIG_SVI_CALIBRATOR` parameter. Currently only one calibrator is implemented,
but adding additional implementations would not be hard.

![fitter_uml](../img/fitter_uml.png)

Finally, we need to perform validation on the final fitted IV surface. The structure of the
final IV validators is analogous to that of the raw IV filters, with a `CompositeFinalIVValidator`
allowing an arbitrary number of validators to be run in succession. Currently only a single
validator is implemented, but the design makes it simple to add new ones.

![final_iv_validation_uml](../img/final_iv_validation_uml.png)

### Ports and Adapters

As mentioned above, the overall design of the system follows the 
[hexagonal architecture](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)), 
or ports and adapters, pattern. This pattern lends its name to the `adapters` package.

The hexagonal architecture describes a design wherein the application core is surrounded
by ports connecting it to the outside world; the ports are abstractions which define the
API, while concrete implementations of the ports, known as adapters, perform the actual
connection to specific external resources.

For example, `AbstractRawIVSupplier` is a 
port representing the location from which the application core retrieves raw
implied vol inputs. I provide an adapter for this port which supplies raw IVs from the
sample data included with the repository, `OptionMetricsRawIVSupplier` (OptionMetrics is
the vendor which provided my sample data). The idea is that the application can easily
be run in many different environments simply by plugging in different adapters. For example,
to run the application live, one would just need to provide an adapter supplying the live
vols and use this instead of `OptionMetricsRawIVSupplier` (and similarly for the other ports).

In our application, we represent ports via abstract base classes. The adapters are the
concrete subclasses of these abstract base classes. The use of abstract base classes is
not strictly necessary to implement this pattern in Python because one can rely on
Python's duck typing, but I find that explicitly defining the abstract base classes aids
in readability by making the ports explicit.

The below UML diagram shows the currently available ports and adapters. In the diagram,
the ports are the top row of abstract classes, and the adapters are the implementations 
beneath them.

![adapters_uml](../img/adapters_uml.png)

## Logic and Functionality

TODO

## Discussion of Possible Extensions

TODO